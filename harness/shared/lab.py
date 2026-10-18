"""Where AI-Lab is, and the calls every study makes to it.

**Where it is comes from configuration, never from this code.** The address of
the AI-Lab manager, the ports of engines a study talks to directly and the
scratch folder are read from AI-Lab's own configuration file, so each value
lives in one place. Which file: the environment variable `AI_LAB_CONFIG`.

- The manager: `$AI_LAB_MANAGER` when set (a study run from another machine),
  else `benchmark.manager_url` in that file, else the loopback address with
  the file's own `port` (the study runs beside the manager).
- Anything else a study needs is in the file's `benchmark` section; a missing
  one stops the study with a message naming it (see `setting`).

The only address written here is the loopback one, which is not a setting.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

LOOPBACK = "127.0.0.1"
CONFIG_VARIABLE = "AI_LAB_CONFIG"
MANAGER_VARIABLE = "AI_LAB_MANAGER"
# What `--help` says about the manager's address.
MANAGER_HELP = (f"AI-Lab manager address; defaults to ${MANAGER_VARIABLE}, then "
                f"benchmark.manager_url or the port in ${CONFIG_VARIABLE}")
API_TIMEOUT_S = 1200
UNLOAD_TIMEOUT_S = 300
UPLOAD_TIMEOUT_S = 1800


class MissingSetting(SystemExit):
    """A study needs a value the configuration does not have. Stops it, naming the value."""


def configuration() -> dict:
    """AI-Lab's configuration file, named by `$AI_LAB_CONFIG`."""
    path = os.environ.get(CONFIG_VARIABLE)
    if not path:
        raise MissingSetting(f"set {CONFIG_VARIABLE} to AI-Lab's config.json")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def setting(name: str) -> str:
    """`benchmark.<name>` from the configuration; stops the study if it is not there."""
    value = configuration().get("benchmark", {}).get(name)
    if value in (None, ""):
        raise MissingSetting(
            f"missing setting benchmark.{name} in ${CONFIG_VARIABLE} ({os.environ[CONFIG_VARIABLE]})")
    return str(value)


def manager_url(given: str | None = None) -> str:
    """The manager's address: `given` (a `--manager` argument), else as the module says."""
    if given:
        return given
    if os.environ.get(MANAGER_VARIABLE):
        return os.environ[MANAGER_VARIABLE]
    config = configuration()
    configured = config.get("benchmark", {}).get("manager_url")
    if configured:
        return str(configured)
    if "port" not in config:
        raise MissingSetting(f"missing setting port in ${CONFIG_VARIABLE}")
    return f"http://{LOOPBACK}:{config['port']}"


def api(base: str, path: str, method: str = "GET", timeout: int = API_TIMEOUT_S,
        body: dict | None = None):
    """One JSON call to the manager; the answer as read."""
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def form_body(fields: dict[str, str], upload: tuple[str, str, bytes]) -> tuple[bytes, str]:
    """A multipart form: text `fields` plus one file, `upload` = (field, file name, bytes).

    Returns the body and its content type. The file's type is guessed from its
    name's suffix (PNG, else WAV).
    """
    field, filename, payload = upload
    kind = "image/png" if filename.lower().endswith(".png") else "audio/wav"
    boundary = "ai-lab-benchmark-" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks += [f"--{boundary}\r\n".encode(),
                   f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                   value.encode(), b"\r\n"]
    chunks += [f"--{boundary}\r\n".encode(),
               f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
               f"Content-Type: {kind}\r\n\r\n".encode(), payload, b"\r\n",
               f"--{boundary}--\r\n".encode()]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def multipart(url: str, fields: dict[str, str], upload: tuple[str, str, bytes],
              timeout: int = UPLOAD_TIMEOUT_S) -> dict:
    """POST a form (see `form_body`); the JSON answer."""
    body, content_type = form_body(fields, upload)
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": content_type})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def read_error(error: Exception) -> str:
    """What went wrong, in the server's own words when it sent any."""
    if isinstance(error, urllib.error.HTTPError):
        try:
            return error.read().decode("utf-8", errors="replace")
        except Exception:
            pass
    return f"{type(error).__name__}: {error}"


def unload_running(base: str) -> list[dict]:
    """Unload every running instance, so a study starts on an empty card."""
    outcomes = []
    for item in api(base, "/api/instances"):
        if not item.get("running"):
            continue
        try:
            result = api(base, f"/api/instances/{item['id']}/unload", "POST", UNLOAD_TIMEOUT_S)
            outcomes.append({"instance": item["id"], "ok": bool(result.get("ok"))})
        except Exception as error:
            outcomes.append({"instance": item["id"], "ok": False, "error": read_error(error)})
    return outcomes


def timed(base: str, instance: str, action: str) -> dict:
    """Load or unload one instance and time it: ok, wall_s, manager_total_ms, error."""
    started = time.perf_counter()
    timeout = UNLOAD_TIMEOUT_S if action == "unload" else API_TIMEOUT_S
    try:
        answer = api(base, f"/api/instances/{instance}/{action}", "POST", timeout)
    except Exception as error:
        return {"ok": False, "wall_s": round(time.perf_counter() - started, 3),
                "error": read_error(error)}
    outcome = {"ok": bool(answer.get("ok")),
               "wall_s": round(time.perf_counter() - started, 3),
               "manager_total_ms": answer.get("total_ms")}
    if not outcome["ok"]:
        outcome["error"] = answer.get("error") or f"{action} failed"
    return outcome


def unreachable(outcome: dict) -> bool:
    """Whether a `timed` call never got an answer (as opposed to an answer saying no)."""
    return not outcome["ok"] and "manager_total_ms" not in outcome


def write_json(path: Path, value) -> None:
    """Write `value` as indented JSON, replacing the file in one step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)
