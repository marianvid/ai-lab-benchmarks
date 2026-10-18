"""The benchmark harness: one script per test, plus what they share (`shared/`).

One package, `harness`: the scripts import their neighbours by their full name
(`harness.shared.lab`), as the tests do, so each module has one name for both.
Every script still runs on its own, as `python3 harness/<script>.py`: it first
puts the repository root on the import path.
"""
