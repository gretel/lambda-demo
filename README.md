# lambda-demo

A visual demo served by a single AWS Lambda function.
WebGL2 metaballs, sine-wave text scroller, procedurally-generated music — all inline, zero dependencies.

## Files

| File | LOC | What |
|---|---|---|
| `lambda_function_readable.py` | ~450 | full source, heavily commented — read this |
| `lambda_function.py` | 6 | base64-obfuscated — deploy this |
| `test_lambda.py` | ~90 | 15 tests |

## Deploy

```bash
zip demo.zip lambda_function.py
```

1. create a Lambda function (Python 3.14 runtime)
2. upload `demo.zip`
3. set handler to `lambda_function.lambda_handler`
4. add a Function URL (or API Gateway trigger)
5. open the URL — your IP and browser appear in the scroller within seconds

To regenerate `lambda_function.py` after editing `lambda_function_readable.py`:
```bash
python3 -c "
import base64, types
src = open('lambda_function_readable.py').read()
b64 = base64.b64encode(src.encode()).decode()
open('lambda_function.py', 'w').write(
  'import base64 as _b, types as _t\n'
  '_m = _t.ModuleType(\"lambda_function_readable\")\n'
  'exec(compile(_b.b64decode(b\\'\\'\\'\\n' + b64 + '\\n\\'\\'\\'\\n).decode(), \"<lambda_function>\", \"exec\"), _m.__dict__)\n'
  'lambda_handler = _m.lambda_handler\n'
)
"
```

## How it works

```
Browser request
  → Lambda extracts client IP + User-Agent from event
  → Prepends personalised greeting to scroll text
  → Returns complete HTML page (text/html)
    → WebGL2 fragment shader renders animated metaballs on GPU
    → Offscreen Canvas2D draws sine-wave scrolling text
    → Text canvas uploaded as WebGL texture, composited over background
    → Web Audio API generates procedural music on first click
```

- **Greeting**: visitor sees their own IP and browser within seconds of the scroll starting.
- **Background**: 5 metaballs in a GLSL fragment shader. Hue rotates over time, randomised on click.
- **Scroller**: each character positioned on a sine wave, drawn per-frame on a hidden canvas, uploaded as a WebGL texture.
- **Music**: procedurally generated every loop — random scale (pentatonic/major), random root, random melody walk, BPM drift. No two loops sound the same.
- **Click**: randomizes color palette + starts audio (browser autoplay policy requires a user gesture).

## Run tests

```
uvx pytest test_lambda.py -v
```

## Key concepts for AWS Cloud Practitioner

- **Lambda**: serverless compute, pay-per-invocation, auto-scaling
- **Function URL**: direct HTTPS endpoint for a Lambda function, no API Gateway needed
- **Event-driven**: Lambda runs in response to events (HTTP request, S3 upload, DynamoDB change, etc.)
- **Event object**: `event["requestContext"]["http"]["sourceIp"]` gives the caller's IP
- **No servers to manage**: AWS handles provisioning, scaling, patching
- **Free tier**: 1M requests + 400,000 GB-seconds per month
