#!/usr/bin/env python3
"""Python problems from HumanEval+ and MBPP+, marked by running the code.

542 problems, nothing graded by opinion: each answer is extracted from its code
block, run against the problem's own test suite, and either passes or does not.

**Why the "+" sets.** The original HumanEval and MBPP ship three or four tests
per problem, which is thin enough that plainly wrong solutions pass and most
models score near the top. EvalPlus regenerated the suites with far more cases,
including the edge cases the originals miss. The scores drop and, more to the
point, they start separating models again.

**Contamination is not the concern here.** These problems are old and are
certainly in every model's training data. That would matter for a study asking
which model reasons best. This one asks how a particular machine behaves under a
particular kind of work, so what matters is that the work is real, standard and
identical for every model — and that both the score and the clock are reported.

Generated code runs as `nobody`, in a throwaway directory, with a timeout. It
is still someone else's code executing on your machine: run this in a container,
not on your laptop.

Usage:
    bench_coding.py <base_url> <label> <concurrency> [options]

Options:
    --data DIR      where get_datasets.py put its files (default ./eval-data)
    --set NAME      humanevalplus, mbppplus or both (default both)
    --limit N       at most N problems per set
    --timeout N     seconds allowed per program (default 30)
    --out FILE      write the result as JSON
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import evalcommon as common

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)

NOBODY_UID = 65534

# Some of the tests import numpy and other ordinary libraries, so the generated
# code has to run against an interpreter that has them. Default to the one
# running this script; override when the sandbox needs a different one.
RUNNER = os.environ.get("BENCH_PYTHON", sys.executable)

# One problem is excluded, and it is the set's fault, not a model's.
# HumanEval/32 asks for the root of a polynomial, and its own reference answer
# fails its own tests when run this way. Validating the harness against all 164
# reference answers gives 163 passes and this one failure, so leaving it in
# would take a point off every model for a problem none of them can pass.
EXCLUDED = {
    "HumanEval/32": "the set's own reference answer fails the set's own tests",
}


def extract_code(text: str) -> str:
    """The code block, or the whole answer if the model wrote bare code."""
    blocks = CODE_RE.findall(text or "")
    return max(blocks, key=len) if blocks else (text or "")


def load(data: pathlib.Path, which: str, limit: int | None) -> list[dict]:
    """Both sets, normalised to one shape: a prompt, and a program that checks it."""
    problems = []

    if which in ("humanevalplus", "both"):
        path = data / "coding" / "humanevalplus.jsonl"
        for index, line in enumerate(path.open(encoding="utf-8")):
            if limit and index >= limit:
                break
            row = json.loads(line)
            if row["task_id"] in EXCLUDED:
                continue
            # HumanEval gives a signature and a docstring; the model completes
            # it. The test file calls check(entry_point).
            problems.append({
                "set": "humanevalplus", "id": row["task_id"],
                "instruction":
                    "Complete this Python function. Reply with the whole "
                    "function, including the signature, in one ```python block. "
                    "No explanation.\n\n```python\n" + row["prompt"] + "```",
                "check": row["test"] + f"\n\ncheck({row['entry_point']})\n",
            })

    if which in ("mbppplus", "both"):
        path = data / "coding" / "mbppplus.jsonl"
        for index, line in enumerate(path.open(encoding="utf-8")):
            if limit and index >= limit:
                break
            row = json.loads(line)
            # MBPP states the task in words and fixes the function name through
            # its assertions, so the model is shown one of them as the contract.
            example = (row.get("test_list") or [""])[0]
            imports = "\n".join(row.get("test_imports") or [])
            problems.append({
                "set": "mbppplus", "id": f"Mbpp/{row['task_id']}",
                "instruction":
                    f"{row['prompt']}\n\nWrite the Python function. It must "
                    f"satisfy this call exactly:\n\n    {example}\n\nReply with "
                    f"the function in one ```python block. No explanation.",
                "check": (imports + "\n" + row["test"] + "\n") if imports else row["test"] + "\n",
            })

    return problems


def run_program(code: str, check: str, timeout: int) -> tuple[bool, str]:
    """Run the answer against the problem's tests, as nobody, then clean up."""
    directory = tempfile.mkdtemp(prefix="codebench_", dir="/tmp")
    path = os.path.join(directory, "prog.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(code + "\n\n" + check + "\nprint('___PASS___')\n")
    try:
        os.chmod(directory, 0o777)
        os.chmod(path, 0o755)
        command = [RUNNER, path]
        if os.geteuid() == 0:
            command = ["setpriv", f"--reuid={NOBODY_UID}", f"--regid={NOBODY_UID}",
                       "--clear-groups", *command]
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=timeout, cwd=directory)
        if "___PASS___" in completed.stdout:
            return True, ""
        lines = (completed.stderr or completed.stdout).strip().splitlines()
        return False, (lines[-1][:180] if lines else "no output")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as error:                          # pragma: no cover
        return False, f"{type(error).__name__}: {error}"[:180]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base"), parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    parser.add_argument("--data", default="./eval-data")
    parser.add_argument("--set", dest="which", default="both",
                        choices=["humanevalplus", "mbppplus", "both"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--out")
    arguments = parser.parse_args()

    problems = load(pathlib.Path(arguments.data), arguments.which, arguments.limit)
    if not problems:
        print("no problems found — run get_datasets.py first", file=sys.stderr)
        return 2
    if os.geteuid() != 0:
        print("note: not root, so generated code runs as you and not as nobody",
              file=sys.stderr)

    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)

    def do(problem: dict) -> dict:
        text = run.ask([{"role": "user", "content": problem["instruction"]}],
                       max_tokens=4096)
        if text is None:
            return {**{k: problem[k] for k in ("set", "id")},
                    "passed": False, "why": "no answer"}
        passed, why = run_program(extract_code(text), problem["check"],
                                  arguments.timeout)
        return {"set": problem["set"], "id": problem["id"],
                "passed": passed, "why": why}

    print(f"\n=== {arguments.label} | {model} | {len(problems)} problems "
          f"| concurrency={arguments.concurrency} ===", flush=True)
    # No warm-up: every problem is different, so a discarded pass would throw
    # away real answers rather than repeat one.
    results = run.go(problems, do, warm=False)

    by_set: dict[str, list[bool]] = {}
    for row in results:
        by_set.setdefault(row["set"], []).append(row["passed"])
    passed = sum(1 for row in results if row["passed"])

    common.report(arguments.out, {
        "test": "coding", "set": "HumanEval+ / MBPP+",
        "label": arguments.label, "model": model,
        "concurrency": arguments.concurrency,
        "problems": len(problems),
        "excluded": EXCLUDED,
        **run.speed(len(problems)),
        "passed": passed,
        "pass_rate": round(passed / len(problems), 4),
        "by_set": {name: {"n": len(marks), "passed": sum(marks),
                          "pass_rate": round(sum(marks) / len(marks), 4)}
                   for name, marks in sorted(by_set.items())},
        "failures": [row for row in results if not row["passed"]][:40],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
