// The lobby's "Waiting for Players" shimmer (owner's markup, Session 49).
// A slow, slanted band of light crosses the label every few seconds; outside
// the band the words sit slightly dimmed. Set on the label by lobby.gd only
// while the room is waiting, and removed the moment it is not.
shader_type canvas_item;
uniform float width = 200.0;    // the label's width, so the band crosses all of it
uniform float period = 4.0;     // seconds per pass, including the rest between passes
uniform float band = 0.22;      // half-width of the light, as a fraction of the label
uniform float rest_dim = 0.72;  // brightness of the words outside the band
varying vec2 local;
void vertex() { local = VERTEX; }
void fragment() {
	// The band travels over the first 60% of the period and is gone for the rest,
	// so it reads as an occasional glint rather than a constant pulse.
	float t = mod(TIME, period) / period / 0.6;
	float pos = mix(-band, 1.0 + band, t);
	float x = local.x / width - local.y / width * 0.35;   // slanted, like light on glass
	float glow = smoothstep(band, 0.0, abs(x - pos));
	COLOR.rgb *= mix(rest_dim, 1.0, glow);
}
