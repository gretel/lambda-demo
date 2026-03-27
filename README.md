# lambda-demo

A visual demo served by a single AWS Lambda function.
WebGL2 metaballs, sine-wave text scroller, procedurally-generated music — all inline, zero dependencies.

## Files

| File | LOC | What |
|---|---|---|
| `lambda_function_readable.py` | ~450 | full source, heavily commented — read this |
| `lambda_function.py` | 6 | base64-obfuscated — deploy this |
| `test_lambda.py` | ~90 | 15 tests |

## Obfuscate Code (Optional)

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

## What it does

- **Greeting**: visitor sees their own IP and browser within seconds of the scroll starting.
- **Background**: 5 metaballs in a GLSL fragment shader. Hue rotates over time, randomised on click.
- **Scroller**: each character positioned on a sine wave, drawn per-frame on a hidden canvas, uploaded as a WebGL texture.
- **Music**: procedurally generated every loop — random scale (pentatonic/major), random root, random melody walk, BPM drift. No two loops sound the same.
- **Click**: randomizes color palette + starts audio (browser autoplay policy requires a user gesture).

## Key concepts for AWS Cloud Practitioner

- **Lambda**: serverless compute, pay-per-invocation, auto-scaling
- **Function URL**: direct HTTPS endpoint for a Lambda function, no API Gateway needed (like in this demo!)
- **Event-driven**: Lambda runs in response to events (HTTP request, S3 upload, DynamoDB change, etc.)
- **Event object**: `event["requestContext"]["http"]["sourceIp"]` gives the caller's IP
- **No servers to manage**: AWS handles provisioning, scaling, patching
- **Free tier**: 1M requests + 400,000 GB-seconds per month

## Run local tests

```
uvx pytest test_lambda.py -v
```

## Deploy (Conceptual)

1. create a Lambda function (Python 3.14 runtime)
2. download [zip file](https://github.com/gretel/lambda-demo/archive/refs/heads/main.zip) containing the code
4. add a Function URL (or API Gateway trigger) using the downloaded coded
5. open the deployment URL
