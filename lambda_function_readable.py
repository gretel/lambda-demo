"""
AWS Cloud Practitioner Demo — Lambda Function
==============================================
A visual demo served by AWS Lambda. Returns a single HTML page with:
  - WebGL2 animated metaball background (fragment shader on GPU)
  - Sine-wave scrolling text overlay (Canvas2D → WebGL texture)
  - Procedurally-generated music (Web Audio API, different every time)
  - Click anywhere to randomize the color palette + start audio

Deploy: zip this file → upload to Lambda → add a Function URL or API Gateway.
"""

# ---------------------------------------------------------------------------
# Scroll text — explains what Lambda is, ~60 seconds at scroll speed
# The greeting (IP + UA) is prepended dynamically by lambda_handler()
# ---------------------------------------------------------------------------
SCROLL_TEXT = (
    "WELCOME TO AWS CLOUD PRACTITIONER  +++  "
    "GREETINGS FROM TEACHER TOM  +++  "
    "WHAT IS AWS LAMBDA?  +++  "
    "SERVERLESS COMPUTE  +++  "
    "NO SERVERS TO MANAGE  +++  "
    "UPLOAD YOUR CODE AND LAMBDA RUNS IT  +++  "
    "PAY ONLY FOR WHAT YOU USE  +++  "
    "SCALES AUTOMATICALLY FROM ZERO TO THOUSANDS  +++  "
    "SUPPORTS PYTHON, NODE, JAVA, GO, RUST  +++  "
    "TRIGGERED BY API GATEWAY, S3, DYNAMODB, SQS, SNS  +++  "
    "MAX 15 MINUTES EXECUTION TIME  +++  "
    "UP TO 10 GB MEMORY  +++  "
    "EVENT DRIVEN ARCHITECTURE  +++  "
    "WRITE FUNCTIONS NOT INFRASTRUCTURE  +++  "
    "THIS PAGE IS SERVED BY A LAMBDA FUNCTION  +++  "
    "JUST 60 LINES OF PYTHON  +++  "
    "THE CLOUD IS THE FUTURE!  +++  "
    "OR IS IT ON PREMISE??  +++  "
    "LAMBDA + API GATEWAY = INSTANT REST API  +++  "
    "LAMBDA + S3 = FILE PROCESSING PIPELINE  +++  "
    "LAMBDA + DYNAMODB = SERVERLESS BACKEND  +++  "
    "ZERO COST WHEN IDLE  +++  "
    "1 MILLION FREE REQUESTS PER MONTH  +++  "
    "KEEP LEARNING KEEP BUILDING  +++       "
)

# ---------------------------------------------------------------------------
# Vertex shader — passes UV coordinates to the fragment shader
# ---------------------------------------------------------------------------
VERTEX_SHADER = """#version 300 es
in vec2 position;
out vec2 uv;

void main() {
    uv = position * 0.5 + 0.5;           // map [-1,1] → [0,1]
    gl_Position = vec4(position, 0, 1);
}
"""

# ---------------------------------------------------------------------------
# Fragment shader — animated metaballs + text texture overlay
#
# How it works:
#   1. For each pixel, compute distance to 5 moving "blob" centers
#   2. Sum inverse distances → creates soft glowing metaball shapes
#   3. Map the value to a color using HSV (hue rotates over time)
#   4. Blend with the text texture on top
#
# Uniforms:
#   t  — time in seconds (drives animation)
#   ho — hue offset (changes on click for palette shift)
#   r  — screen resolution (for aspect ratio correction)
#   x  — text texture (from offscreen Canvas2D)
# ---------------------------------------------------------------------------
FRAGMENT_SHADER = """#version 300 es
precision highp float;

uniform float t;          // time
uniform float ho;         // hue offset (randomized on click)
uniform vec2  r;          // resolution
uniform sampler2D x;      // text overlay texture

in  vec2 uv;
out vec4 fragColor;

// Convert HSV to RGB
vec3 hsv2rgb(float h, float s, float v) {
    vec3 k = vec3(1.0, 0.667, 0.333);
    vec3 p = clamp(abs(fract(h + k) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
    return v * mix(vec3(1.0), p, s);
}

void main() {
    // Normalize coordinates to [-1, 1], correct for aspect ratio
    vec2 p = uv * 2.0 - 1.0;
    p.x *= r.x / r.y;

    // Accumulate metaball field from 5 animated blobs
    float field = 0.0;
    for (int i = 0; i < 5; i++) {
        float fi = float(i);
        vec2 center = vec2(
            sin(t * 0.4 + fi * 1.3) * 0.6,
            cos(t * 0.5 + fi * 1.7) * 0.5
        );
        field += 0.12 / length(p - center);   // inverse distance
    }
    field = clamp(field, 0.0, 1.0);

    // Color: hue depends on field strength + time + click offset
    vec3 background = hsv2rgb(field * 0.3 + t * 0.05 + ho, 0.7, field * 0.8);

    // Sample text overlay and blend
    vec4 text = texture(x, vec2(uv.x, 1.0 - uv.y));
    fragColor = vec4(mix(background, text.rgb, text.a), 1.0);
}
"""

# ---------------------------------------------------------------------------
# HTML page template — everything inline, no external dependencies
# ---------------------------------------------------------------------------
HTML = (
    '<!DOCTYPE html><html><head><meta charset="utf-8">'
    "<style>"
    "  * { margin: 0; overflow: hidden; }"
    "  canvas { display: block; cursor: pointer; }"
    "  #hint { position: fixed; bottom: 40px; width: 100%; text-align: center;"
    "    color: #ff0; font: 1.2em monospace; opacity: .7; pointer-events: none;"
    "    transition: opacity 1s; }"
    "</style>"
    "</head><body>"
    '<canvas id="c"></canvas>'
    '<div id="hint">click for sound</div>'
    "<script>"
    + r"""
// =====================================================================
// SETUP
// =====================================================================
const WIDTH  = innerWidth;
const HEIGHT = innerHeight;
const canvas = document.getElementById('c');
const gl     = canvas.getContext('webgl2');

canvas.width  = WIDTH;
canvas.height = HEIGHT;

let time      = 0;       // animation clock (seconds)
let scrollX   = WIDTH;   // horizontal scroll position
let hueOffset = 0;       // palette shift (randomized on click)
let audioCtx  = null;    // created on first click (browser policy)

// The scrolling message: greeting (IP/UA injected by Lambda) + static content
const MESSAGE = `{{DYN}}` + `"""
    + SCROLL_TEXT
    + r"""`;

// =====================================================================
// WEBGL PIPELINE
// =====================================================================

// Compile a shader from source
function compileShader(source, type) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    return shader;
}

// Build the shader program
const program = gl.createProgram();
gl.attachShader(program, compileShader(`"""
    + VERTEX_SHADER
    + """`, gl.VERTEX_SHADER));
gl.attachShader(program, compileShader(`"""
    + FRAGMENT_SHADER
    + """`, gl.FRAGMENT_SHADER));
gl.linkProgram(program);
gl.useProgram(program);

// Full-screen quad (two triangles as a triangle strip)
const quadBuffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
gl.bufferData(gl.ARRAY_BUFFER,
    new Float32Array([-1,-1, 1,-1, -1,1, 1,1]),  // 4 corners
    gl.STATIC_DRAW);

const posAttr = gl.getAttribLocation(program, 'position');
gl.enableVertexAttribArray(posAttr);
gl.vertexAttribPointer(posAttr, 2, gl.FLOAT, false, 0, 0);

// Uniform locations
const uTime = gl.getUniformLocation(program, 't');
const uRes  = gl.getUniformLocation(program, 'r');
const uHue  = gl.getUniformLocation(program, 'ho');

gl.uniform2f(uRes, WIDTH, HEIGHT);
gl.viewport(0, 0, WIDTH, HEIGHT);

// =====================================================================
// TEXT OVERLAY (offscreen Canvas2D → WebGL texture)
// =====================================================================

// We draw text on a hidden 2D canvas, then upload it as a texture
// so WebGL can composite it over the metaball background.
const textCanvas = document.createElement('canvas');
const textCtx    = textCanvas.getContext('2d');
textCanvas.width  = WIDTH;
textCanvas.height = HEIGHT;

const textTexture = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, textTexture);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

// Draw the sine-wave scroller + footer text
function drawTextOverlay() {
    textCtx.clearRect(0, 0, WIDTH, HEIGHT);
    textCtx.font = 'bold 60px monospace';

    const charWidth = 36;

    for (let i = 0; i < MESSAGE.length; i++) {
        const x = scrollX + i * charWidth;

        // Skip characters that are off-screen
        if (x < -charWidth || x > WIDTH + charWidth) continue;

        // Sine wave: vertical offset based on horizontal position + time
        const y = HEIGHT / 2 + Math.sin(x * 0.008 + time * 2) * 80;

        // Shadow (offset, semi-transparent)
        textCtx.globalAlpha = 0.35;
        textCtx.fillStyle = '#aa0';
        textCtx.fillText(MESSAGE[i], x - 2, y + 2);

        // Main character (bright yellow)
        textCtx.globalAlpha = 1;
        textCtx.fillStyle = '#ff0';
        textCtx.fillText(MESSAGE[i], x, y);
    }

    // Footer
    textCtx.globalAlpha = 0.4;
    textCtx.fillStyle = '#ff0';
    textCtx.font = '16px monospace';
    textCtx.fillText('AWS LAMBDA // PYTHON // CLOUD', 10, HEIGHT - 20);
    textCtx.globalAlpha = 1;

    // Advance scroll position, loop when done
    scrollX -= 3;
    if (scrollX < -MESSAGE.length * charWidth) scrollX = WIDTH;

    // Upload to WebGL as texture
    gl.texImage2D(
        gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, textCanvas
    );
}

// =====================================================================
// ANIMATION LOOP
// =====================================================================

function frame() {
    time += 0.016;                          // ~60fps increment
    drawTextOverlay();                      // update text texture
    gl.uniform1f(uTime, time);              // pass time to shader
    gl.uniform1f(uHue, hueOffset);          // pass hue offset
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); // render full-screen quad
    requestAnimationFrame(frame);
}

// =====================================================================
// MUSIC — procedurally generated (different every time)
//
// How it works:
//   - A random "root" note and scale (pentatonic or major) is chosen
//   - Each loop, a new melody is generated by random-walking up/down
//     the scale, with random note lengths and occasional rests
//   - Bass plays the root and fifth of the current chord
//   - BPM drifts slowly each loop for organic feel
//   - Filter cutoff varies per note for texture
// =====================================================================

// MIDI note number → frequency in Hz
function midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
}

// Play a single note with envelope and lowpass filter
function playNote(freq, startTime, duration, waveType, volume, filterFreq) {
    const osc    = audioCtx.createOscillator();
    const gain   = audioCtx.createGain();
    const filter = audioCtx.createBiquadFilter();

    osc.type = waveType;
    osc.frequency.value = freq;

    filter.type = 'lowpass';
    filter.frequency.value = filterFreq || 1800;
    filter.Q.value = 1;

    // ADSR-ish envelope
    gain.gain.setValueAtTime(0, startTime);
    gain.gain.linearRampToValueAtTime(volume, startTime + 0.02);
    gain.gain.setValueAtTime(volume, startTime + duration - 0.05);
    gain.gain.linearRampToValueAtTime(0, startTime + duration);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start(startTime);
    osc.stop(startTime + duration + 0.01);
}

// Pentatonic and major scale intervals (semitone steps from root)
const SCALES = [
    [0, 2, 4, 7, 9],          // pentatonic major
    [0, 3, 5, 7, 10],         // pentatonic minor
    [0, 2, 4, 5, 7, 9, 11],   // major
    [0, 2, 3, 5, 7, 8, 10],   // natural minor
];

// Pick a random root and scale once at startup
let scaleIntervals = SCALES[Math.floor(Math.random() * SCALES.length)];
let rootNote       = 48 + Math.floor(Math.random() * 7);  // C3–G3
let bpm            = 90 + Math.floor(Math.random() * 40); // 90–130 BPM
let melodyPos      = 0;  // current scale position (random walk)

// Build the full note set across 3 octaves from root
function buildScale(root, intervals) {
    const notes = [];
    for (let oct = 0; oct < 3; oct++) {
        for (const step of intervals) {
            notes.push(root + oct * 12 + step);
        }
    }
    return notes;
}

// Schedule one loop of generated music, then repeat
function playMusicLoop() {
    const beat     = 60 / bpm;
    const loopLen  = 8;  // beats per loop
    const T        = audioCtx.currentTime + 0.05;
    const scale    = buildScale(rootNote, scaleIntervals);

    // --- melody: random walk along scale ---
    let pos = Math.max(0, Math.min(scale.length - 1,
        Math.floor(scale.length * 0.4) + Math.floor(Math.random() * 4)));
    let currentBeat = 0;

    while (currentBeat < loopLen) {
        // Random duration: eighth, quarter, or dotted quarter
        const dur = [0.5, 1, 1.5][Math.floor(Math.random() * 3)];
        if (currentBeat + dur > loopLen) break;

        // 15% chance of rest
        if (Math.random() > 0.15) {
            const midi = scale[pos];
            const filterFreq = 800 + Math.random() * 1400;  // 800–2200 Hz
            playNote(midiToFreq(midi), T + currentBeat * beat,
                dur * beat * 0.85, 'sine', 0.07, filterFreq);
        }

        // Random walk: step up, down, or jump
        const step = Math.floor(Math.random() * 5) - 2;  // -2 to +2
        pos = Math.max(0, Math.min(scale.length - 1, pos + step));
        currentBeat += dur;
    }

    // --- bass: root and fifth on beats 0, 2, 4, 6 ---
    const bassNotes = [rootNote, rootNote + 7, rootNote - 2, rootNote + 5];
    for (let i = 0; i < 4; i++) {
        const midi = bassNotes[i % bassNotes.length];
        playNote(midiToFreq(midi - 12), T + i * 2 * beat,
            1.6 * beat, 'triangle', 0.09, 600);
    }

    // --- chord pad: random voicing every 4 beats ---
    for (let bar = 0; bar < 2; bar++) {
        const rootIdx = Math.floor(Math.random() * scaleIntervals.length);
        const chord = [0, 2, 4].map(i =>
            rootNote + scaleIntervals[(rootIdx + i) % scaleIntervals.length]
        );
        for (const midi of chord) {
            playNote(midiToFreq(midi), T + bar * 4 * beat,
                3.5 * beat, 'sine', 0.022, 1200);
        }
    }

    // Drift BPM slightly each loop for organic feel
    bpm += (Math.random() - 0.5) * 4;
    bpm = Math.max(80, Math.min(140, bpm));

    setTimeout(playMusicLoop, loopLen * beat * 1000);
}

// =====================================================================
// INTERACTION
// =====================================================================

// Click anywhere:
//   - First click starts audio (browser requires user gesture)
//   - Every click randomizes the background color palette
canvas.onclick = () => {
    if (!audioCtx) {
        audioCtx = new AudioContext();
        playMusicLoop();
        document.getElementById('hint').style.opacity = 0;
    }
    hueOffset = Math.random();
};

// Start the visual loop immediately (audio waits for click)
frame();
"""
    + "</script></body></html>"
)


import html as _h


def _abbreviate_user_agent(raw):
    """
    Abbreviate a user-agent string to just the browser name and major version.

    Example: 'Mozilla/5.0 ... Chrome/120.0.6099.71 Safari/537.36' → 'Chrome/120'

    Checks browsers in priority order because Chrome UA strings also contain
    'Safari/', Edge contains 'Chrome/', etc.
    """
    for browser in ("Edge", "OPR", "Chrome", "Firefox", "Safari"):
        for token in raw.split():
            if token.startswith(browser + "/"):
                return token.split(".")[0]
    return raw[:30]


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Extracts the caller's IP address and user-agent from the Lambda event,
    injects them into the scrolling text, and returns the HTML page.

    The event structure for Function URLs:
        event["requestContext"]["http"]["sourceIp"]  → client IP
        event["headers"]["user-agent"]               → browser UA string
    """
    # Extract IP — try Function URL format, then API Gateway x-forwarded-for
    ip = (
        event.get("requestContext", {}).get("http", {}).get("sourceIp")
        or event.get("headers", {}).get("x-forwarded-for", "").split(",")[0]
        or "127.0.0.1"
    )

    # Extract and abbreviate user-agent
    ua = _abbreviate_user_agent(event.get("headers", {}).get("user-agent", "local"))

    # Greeting prepended to scroll — visitor sees it within seconds (HTML-escaped for XSS safety)
    dynamic_text = _h.escape(f"       HI TO {ip} USING {ua}  +++  ")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": HTML.replace("{{DYN}}", dynamic_text),
    }
