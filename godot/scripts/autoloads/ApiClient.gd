## ApiClient -- Global singleton.
## Wraps all HTTP calls to the FastAPI backend.
## The Godot client never talks to the Claude API directly -- all AI calls
## go through this singleton to server/main.py.
##
## Callbacks receive (error: String, data).
## error is "" on success, or an error message on failure.
##
## SESSION ANNOTATION -- Phase 2:
## SERVER_URL is localhost for dev. Change to deployed URL before shipping.

extends Node

const SERVER_URL_DEFAULT: String = "http://localhost:8000"
const REQUEST_TIMEOUT: float = 120.0   ## seconds; generation can take 60-90s
var server_url: String = SERVER_URL_DEFAULT

func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load("user://server_config.cfg") == OK:
		server_url = cfg.get_value("server", "url", SERVER_URL_DEFAULT)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Synchronous generation (kept for reference; prefer generate_mystery_async).
func generate_mystery(prompt: String, cinematic_brief: bool, callback: Callable) -> void:
	var body := JSON.stringify({"prompt": prompt, "cinematic_brief": cinematic_brief})
	_post("/generate", body, callback)

## Async generation: returns {job_id} immediately; poll with poll_job().
func generate_mystery_async(prompt: String, cinematic_brief: bool, callback: Callable) -> void:
	var body := JSON.stringify({"prompt": prompt, "cinematic_brief": cinematic_brief})
	_post("/generate/async", body, callback)

## Poll a running job. callback receives (error, {status, stage, result, error}).
func poll_job(job_id: String, callback: Callable) -> void:
	_do_request("/jobs/" + job_id, HTTPClient.METHOD_GET, "", callback)

func interrogate(mystery: Dictionary, character_name: String, question: String, callback: Callable) -> void:
	var body := JSON.stringify({"mystery": mystery, "character_name": character_name, "question": question})
	_post("/interrogate", body, callback)

func rate_mystery(slug: String, rating: int, callback: Callable) -> void:
	var body := JSON.stringify({"mystery_slug": slug, "rating": rating})
	_post("/rate", body, callback)

func list_mysteries(callback: Callable) -> void:
	_do_request("/mysteries", HTTPClient.METHOD_GET, "", callback)

func get_mystery(slug: String, callback: Callable) -> void:
	_do_request("/mysteries/" + slug, HTTPClient.METHOD_GET, "", callback)

func health_check(callback: Callable) -> void:
	_do_request("/health", HTTPClient.METHOD_GET, "", callback)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

func _post(path: String, body: String, callback: Callable) -> void:
	_do_request(path, HTTPClient.METHOD_POST, body, callback)

func _do_request(path: String, method: int, body: String, callback: Callable) -> void:
	var req := HTTPRequest.new()
	req.timeout = REQUEST_TIMEOUT
	add_child(req)
	req.request_completed.connect(_on_done.bind(req, callback))
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err: int
	if method == HTTPClient.METHOD_POST:
		err = req.request(server_url + path, headers, HTTPClient.METHOD_POST, body)
	else:
		err = req.request(server_url + path)
	if err != OK:
		req.queue_free()
		callback.call("HTTP request failed (code %d)" % err, {})

func _on_done(result: int, code: int, _headers: PackedStringArray, body_bytes: PackedByteArray, req: HTTPRequest, callback: Callable) -> void:
	req.queue_free()
	if result == HTTPRequest.RESULT_TIMEOUT:
		callback.call("Request timed out after %ds — server may still be generating." % int(REQUEST_TIMEOUT), {})
		return
	if result != HTTPRequest.RESULT_SUCCESS:
		callback.call("Network error (result=%d)" % result, {})
		return
	if code < 200 or code >= 300:
		callback.call("Server error %d: %s" % [code, body_bytes.get_string_from_utf8()], {})
		return
	var json := JSON.new()
	if json.parse(body_bytes.get_string_from_utf8()) != OK:
		callback.call("JSON parse error: " + json.get_error_message(), {})
		return
	callback.call("", json.data)
