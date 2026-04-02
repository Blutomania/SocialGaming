## ApiClient — Global singleton.
## Wraps all HTTP calls to the FastAPI backend.
## The Godot client never talks to the Claude API directly — all AI calls
## go through this singleton → server/main.py.
##
## Usage:
##   ApiClient.generate_mystery("a murder on a train", false, _on_mystery_ready)
##   ApiClient.interrogate(mystery_dict, "Dr. Watson", "Where were you?", _on_reply)
##
## Callbacks receive (error: String, data: Dictionary).
## error is "" on success, or an error message on failure.
##
## SESSION ANNOTATION — Phase 2:
## SERVER_URL is localhost for dev. Change to deployed URL before shipping.
## Add a settings screen in Phase 3 that lets the player configure it, or
## read from a config file.

extends Node

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
## Backend URL. Override via environment or a local config file.
const SERVER_URL_DEFAULT: String = "http://localhost:8000"

var server_url: String = SERVER_URL_DEFAULT

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
## One HTTPRequest node per in-flight request. We keep a pool so multiple
## requests can be in-flight simultaneously (e.g. listing + generating).
var _pool: Array = []

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	# Allow SERVER_URL to be overridden by a local config file
	# (useful for pointing dev builds at a staging server).
	var config_path := "user://server_config.cfg"
	var cfg := ConfigFile.new()
	if cfg.load(config_path) == OK:
		server_url = cfg.get_value("server", "url", SERVER_URL_DEFAULT)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Generate a new mystery.
## callback: func(error: String, mystery: Dictionary)
func generate_mystery(prompt: String, cinematic_brief: bool, callback: Callable) -> void:
	var body := JSON.stringify({
		"prompt": prompt,
		"cinematic_brief": cinematic_brief,
	})
	_post("/generate", body, callback)


## Ask a character a question.
## callback: func(error: String, data: Dictionary)  — data has "response" key
func interrogate(
		mystery: Dictionary,
		character_name: String,
		question: String,
		callback: Callable) -> void:
	var body := JSON.stringify({
		"mystery": mystery,
		"character_name": character_name,
		"question": question,
	})
	_post("/interrogate", body, callback)


## Save a viability rating for a mystery.
## callback: func(error: String, data: Dictionary)
func rate_mystery(slug: String, rating: int, callback: Callable) -> void:
	var body := JSON.stringify({
		"mystery_slug": slug,
		"rating": rating,
	})
	_post("/rate", body, callback)


## List all saved mysteries.
## callback: func(error: String, data: Array)
func list_mysteries(callback: Callable) -> void:
	_get("/mysteries", callback)


## Load a saved mystery by slug.
## callback: func(error: String, mystery: Dictionary)
func get_mystery(slug: String, callback: Callable) -> void:
	_get("/mysteries/" + slug, callback)


## Quick health check (no AI calls).
## callback: func(error: String, data: Dictionary)
func health_check(callback: Callable) -> void:
	_get("/health", callback)

# ---------------------------------------------------------------------------
# Internal HTTP helpers
# ---------------------------------------------------------------------------

func _get_request_node() -> HTTPRequest:
	var req := HTTPRequest.new()
	add_child(req)
	_pool.append(req)
	return req

func _post(path: String, body: String, callback: Callable) -> void:
	var req := _get_request_node()
	var headers := PackedStringArray(["Content-Type: application/json"])
	var on_complete := func(result, code, _headers, body_bytes):
		_pool.erase(req)
		req.queue_free()
		_handle_response(result, code, body_bytes, callback)
	req.request_completed.connect(on_complete, CONNECT_ONE_SHOT)
	var err := req.request(server_url + path, headers, HTTPClient.METHOD_POST, body)
	if err != OK:
		_pool.erase(req)
		req.queue_free()
		callback.call("HTTP request failed (code %d)" % err, {})

func _get(path: String, callback: Callable) -> void:
	var req := _get_request_node()
	var on_complete := func(result, code, _headers, body_bytes):
		_pool.erase(req)
		req.queue_free()
		_handle_response(result, code, body_bytes, callback)
	req.request_completed.connect(on_complete, CONNECT_ONE_SHOT)
	var err := req.request(server_url + path)
	if err != OK:
		_pool.erase(req)
		req.queue_free()
		callback.call("HTTP request failed (code %d)" % err, {})

func _handle_response(
		result: int,
		code: int,
		body_bytes: PackedByteArray,
		callback: Callable) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		callback.call("Network error (result=%d)" % result, {})
		return
	if code < 200 or code >= 300:
		var body_text := body_bytes.get_string_from_utf8()
		callback.call("Server error %d: %s" % [code, body_text], {})
		return
	var json := JSON.new()
	var parse_err := json.parse(body_bytes.get_string_from_utf8())
	if parse_err != OK:
		callback.call("JSON parse error: " + json.get_error_message(), {})
		return
	callback.call("", json.data)
