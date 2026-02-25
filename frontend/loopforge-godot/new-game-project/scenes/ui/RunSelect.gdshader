shader_type canvas_item;

uniform float top_alpha = 0.0;
uniform float bottom_alpha = 0.85;

void fragment() {
	float t = UV.y; // 0 at top, 1 at bottom
	float a = mix(top_alpha, bottom_alpha, smoothstep(0.0, 1.0, t));
	COLOR = vec4(0.0, 0.0, 0.0, a);
}
