"""Tests of the harness's modules and of the report generators.

Run from the repository root: `python3 -m pytest` (pytest.ini names this folder
and puts the root on the import path). The harness is one package, `harness`:
the scripts import their neighbours as `harness.shared.lab` and so on, and the
tests import them the same way, so every module has one name.
"""
