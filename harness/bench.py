#!/usr/bin/env python3
"""Measure an OpenAI-compatible inference server the way a coding agent uses it.

Two numbers matter and they are different things:
  prefill  -- how fast the model reads the prompt (agent pastes whole files)
  decode   -- how fast the model writes the answer (agent waits for the patch)

Usage: bench.py <base_url> <label> [out.json]
"""
import json
import sys
import time
import urllib.error
import urllib.request


def post(base, path, payload):
    """Reasoning models otherwise spend the whole budget thinking, and stream
    that thinking on a separate field, which hides the real first token."""
    body = dict(payload)
    body["chat_template_kwargs"] = {"enable_thinking": False}
    for attempt in (body, payload):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(attempt).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer none"},
        )
        try:
            return urllib.request.urlopen(req, timeout=1800)
        except urllib.error.HTTPError as e:
            if e.code in (400, 422) and attempt is body:
                continue
            raise
    raise RuntimeError("both attempts failed")

def model_name(base):
    """The id of the model the server answers with."""
    with urllib.request.urlopen(base + "/v1/models", timeout=60) as r:
        return json.load(r)["data"][0]["id"]

# A prompt that looks like real agent work: a chunk of source plus a request.
UNIT = (
    "def process_record(record, config, cache):\n"
    "    key = record.get('id')\n"
    "    if key is None:\n"
    "        raise ValueError('record without id')\n"
    "    if key in cache:\n"
    "        return cache[key]\n"
    "    result = {'id': key, 'fields': {}}\n"
    "    for name, spec in config['fields'].items():\n"
    "        raw = record.get(name)\n"
    "        if raw is None and spec.get('required'):\n"
    "            raise KeyError(name)\n"
    "        result['fields'][name] = spec['parse'](raw) if raw is not None else None\n"
    "    cache[key] = result\n"
    "    return result\n\n"
)

def make_prompt(repeats):
    """A prompt of `repeats` copies of the code unit, ending in the task."""
    body = "".join(f"# --- module {i} ---\n" + UNIT for i in range(repeats))
    return (
        "Here is part of a Python codebase:\n\n```python\n" + body + "```\n\n"
        "Rewrite process_record so that parse failures are collected into a list "
        "of errors instead of raising on the first one. Return only the new function."
    )

def events(resp):
    """The JSON objects of a server-sent event stream, up to `[DONE]`."""
    for raw in resp:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except json.JSONDecodeError:
            continue


def pieces(obj):
    """How many text pieces (answer or reasoning) one stream object carries."""
    count = 0
    for ch in obj.get("choices", []):
        dl = ch.get("delta", {})
        if dl.get("content") or dl.get("reasoning_content"):
            count += 1
    return count


def speeds(tag, usage, n_out, ttft, total):
    """The record for one request: tokens, first-token time and both speeds."""
    p_in = usage.get("prompt_tokens")
    p_out = usage.get("completion_tokens", n_out)
    decode_s = total - (ttft or 0)
    return {
        "test": tag,
        "prompt_tokens": p_in,
        "output_tokens": p_out,
        "ttft_s": round(ttft, 3) if ttft else None,
        "total_s": round(total, 2),
        "prefill_tok_s": round(p_in / ttft, 1) if (p_in and ttft) else None,
        "decode_tok_s": round((p_out - 1) / decode_s, 1) if decode_s > 0 and p_out > 1 else None,
    }


def run(base, model, prompt, max_tokens, tag):
    """One request, timed; its prefill and decode speed under `tag`."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    t0 = time.perf_counter()
    ttft = None
    n_out = 0
    usage = {}
    resp = post(base, "/v1/chat/completions", payload)
    for obj in events(resp):
        if obj.get("usage"):
            usage = obj["usage"]
        count = pieces(obj)
        if count and ttft is None:
            ttft = time.perf_counter() - t0
        n_out += count
    return speeds(tag, usage, n_out, ttft, time.perf_counter() - t0)

# The prompt and the answer share the context window, so the longest prompt has
# to leave room for the answer. At about 153 tokens per repeat, 190 repeats is
# roughly 29 000 tokens, which fits a 32 768-token window with the 256-token
# answer and some framing. 220 repeats did not, and every model refused it with
# HTTP 400.
TESTS = [
    (make_prompt(2),   256, "short prompt (~500 tok)"),
    (make_prompt(60),  256, "medium prompt (~9k tok)"),
    (make_prompt(190), 256, "long prompt (~29k tok)"),
]



def measure(base, model, tag, prompt, max_tokens):
    """One test's record: its speeds, or the error that stopped it."""
    try:
        return run(base, model, prompt, max_tokens, tag)
    except Exception as e:
        return {"test": tag, "error": repr(e)}


def main(argv):
    """Warm up, run the three prompt sizes, print each and write them all."""
    base, label = argv[1], argv[2]
    out = argv[3] if argv[3:] else None
    model = model_name(base)
    results = {"label": label, "model": model, "runs": []}
    print(f"\n=== {label} | {model} ===", flush=True)
    # one untimed warm-up so the first real number is not a cold start
    try:
        run(base, model, make_prompt(2), 16, "warmup")
    except Exception as e:
        print("warmup failed:", e, flush=True)
    for prompt, mt, tag in TESTS:
        r = measure(base, model, tag, prompt, mt)
        results["runs"].append(r)
        print(json.dumps(r), flush=True)
    if out:
        with open(out, "w") as f:
            json.dump(results, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
