#!/usr/bin/env python3
"""Fetch the three public evaluation sets this study measures against.

Nothing here is redistributed. Each set is downloaded from the people who made
it, into a local cache, and the benchmark scripts read it from there. That keeps
the licence question where it belongs — with the original authors — and keeps
this repository to code and results.

    FLORES-200   sentences translated by people into 200 languages.
                 CC BY-SA 4.0. Downloaded from Meta's own release, because the
                 Hugging Face copies require an account.
                 https://github.com/facebookresearch/flores

    SIB-200      the same sentences, labelled by people with one of seven
                 topics. CC BY-SA 4.0.
                 https://huggingface.co/datasets/Davlan/sib200

    Belebele     reading-comprehension questions over passages, four options
                 each, one correct, written and checked by people.
                 CC BY-SA 4.0.
                 https://huggingface.co/datasets/facebook/belebele

    HumanEval+   164 Python problems, each with a signature, a description and
    MBPP+        a suite of tests. 378 more of the same, simpler. Both are the
                 standard sets with EvalPlus's much larger test suites, which
                 is the point: the original tests are so thin that most models
                 pass everything and the scores stop separating anything.
                 Apache 2.0.
                 https://github.com/evalplus/evalplus

All three are built on the same FLORES passages, which is why a model can be
compared across them: understanding, categorising and translating the *same*
text.

Run it once:

    python3 get_datasets.py --out ./eval-data

Then the benchmark scripts read from that directory.
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "ai-lab-benchmarks/1.0 (https://github.com/marianvid/ai-lab-benchmarks)"

FLORES_TARBALL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
SIB_FILE = ("https://huggingface.co/datasets/Davlan/sib200/resolve/main/"
            "data/{code}/test.tsv")
BELEBELE_FILE = ("https://huggingface.co/datasets/facebook/belebele/resolve/main/"
                 "data/{code}.jsonl")
HUMANEVAL_FILE = ("https://huggingface.co/datasets/evalplus/humanevalplus/"
                  "resolve/main/test.jsonl")
# MBPP+ is published only as parquet, which would mean a dependency for one
# file. The rows service returns the same content as JSON, a page at a time.
ROWS_SERVICE = "https://datasets-server.huggingface.co/rows"

# The twenty languages, chosen for reach and for variety of writing system.
# The script code matters: the same sentence costs very different numbers of
# tokens in Han, Devanagari or Latin, and that difference is one of the things
# worth measuring. Keys are the everyday two-letter codes; values are the
# FLORES codes all three datasets use.
LANGUAGES = {
    "en": ("eng_Latn", "English",    "Latin"),
    "zh": ("zho_Hans", "Chinese",    "Han"),
    "hi": ("hin_Deva", "Hindi",      "Devanagari"),
    "es": ("spa_Latn", "Spanish",    "Latin"),
    "ar": ("arb_Arab", "Arabic",     "Arabic"),
    "fr": ("fra_Latn", "French",     "Latin"),
    "bn": ("ben_Beng", "Bengali",    "Bengali"),
    "pt": ("por_Latn", "Portuguese", "Latin"),
    "ru": ("rus_Cyrl", "Russian",    "Cyrillic"),
    "ja": ("jpn_Jpan", "Japanese",   "Japanese"),
    "de": ("deu_Latn", "German",     "Latin"),
    "ko": ("kor_Hang", "Korean",     "Hangul"),
    "tr": ("tur_Latn", "Turkish",    "Latin"),
    "vi": ("vie_Latn", "Vietnamese", "Latin"),
    "ta": ("tam_Taml", "Tamil",      "Tamil"),
    "th": ("tha_Thai", "Thai",       "Thai"),
    "pl": ("pol_Latn", "Polish",     "Latin"),
    "uk": ("ukr_Cyrl", "Ukrainian",  "Cyrillic"),
    "ro": ("ron_Latn", "Romanian",   "Latin"),
    "lt": ("lit_Latn", "Lithuanian", "Latin"),
}


def fetch(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_flores(out: pathlib.Path, codes: list[str]) -> None:
    """FLORES arrives as one tarball of plain text, one line per sentence."""
    target = out / "flores"
    if all((target / f"{code}.txt").exists() for code in codes):
        print("  flores: already here")
        return
    target.mkdir(parents=True, exist_ok=True)
    print(f"  flores: downloading {FLORES_TARBALL} (~25 MB)")
    blob = fetch(FLORES_TARBALL, timeout=600)
    wanted = {f"{code}.devtest": code for code in codes}
    found = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive:
            name = member.name.rsplit("/", 1)[-1]
            if name in wanted:
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                (target / f"{wanted[name]}.txt").write_bytes(handle.read())
                found += 1
    print(f"  flores: {found}/{len(codes)} languages")
    missing = [c for c in codes if not (target / f"{c}.txt").exists()]
    if missing:
        print(f"  flores: MISSING {missing}", file=sys.stderr)


def get_per_language(out: pathlib.Path, codes: list[str], name: str,
                     template: str, suffix: str) -> None:
    """SIB-200 and Belebele are one file per language, fetched one at a time."""
    target = out / name
    target.mkdir(parents=True, exist_ok=True)
    got, failed = 0, []
    for code in codes:
        path = target / f"{code}{suffix}"
        if path.exists() and path.stat().st_size > 0:
            got += 1
            continue
        try:
            path.write_bytes(fetch(template.format(code=code)))
            got += 1
        except urllib.error.HTTPError as error:
            failed.append(f"{code} ({error.code})")
        print(f"  {name}: {got}/{len(codes)}", end="\r", file=sys.stderr)
    print(f"  {name}: {got}/{len(codes)} languages" + (" " * 20))
    if failed:
        print(f"  {name}: MISSING {failed}", file=sys.stderr)


def get_coding(out: pathlib.Path) -> None:
    """The two Python sets. Neither depends on language, so neither is per-language."""
    target = out / "coding"
    target.mkdir(parents=True, exist_ok=True)

    path = target / "humanevalplus.jsonl"
    if path.exists() and path.stat().st_size > 0:
        print("  humanevalplus: already here")
    else:
        path.write_bytes(fetch(HUMANEVAL_FILE, timeout=300))
        print(f"  humanevalplus: {sum(1 for _ in path.open())} problems")

    path = target / "mbppplus.jsonl"
    if path.exists() and path.stat().st_size > 0:
        print("  mbppplus: already here")
        return
    collected, offset = [], 0
    while True:
        query = urllib.parse.urlencode({"dataset": "evalplus/mbppplus",
                                        "config": "default", "split": "test",
                                        "offset": offset, "length": 100})
        page = json.loads(fetch(f"{ROWS_SERVICE}?{query}", timeout=120))
        collected.extend(row["row"] for row in page["rows"])
        offset += 100
        if offset >= page.get("num_rows_total", 0):
            break
    with path.open("w", encoding="utf-8") as handle:
        for row in collected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  mbppplus: {len(collected)} problems")


def write_manifest(out: pathlib.Path, codes: list[str]) -> None:
    """What was downloaded, from where, and under what terms."""
    manifest = {
        "note": "Downloaded from the original publishers. Not redistributed by "
                "this repository. Cite the sources below if you publish results.",
        "languages": {two: {"flores_code": code, "name": name, "script": script}
                      for two, (code, name, script) in LANGUAGES.items()
                      if code in codes},
        "sources": [
            {"name": "FLORES-200", "licence": "CC BY-SA 4.0",
             "url": FLORES_TARBALL,
             "home": "https://github.com/facebookresearch/flores",
             "what": "sentences translated by people; the reference for chrF++"},
            {"name": "SIB-200", "licence": "CC BY-SA 4.0",
             "home": "https://huggingface.co/datasets/Davlan/sib200",
             "what": "the same sentences, labelled by people with one of seven topics"},
            {"name": "Belebele", "licence": "CC BY-SA 4.0",
             "home": "https://huggingface.co/datasets/facebook/belebele",
             "what": "reading-comprehension questions over passages, four options each"},
            {"name": "HumanEval+ and MBPP+", "licence": "Apache 2.0",
             "home": "https://github.com/evalplus/evalplus",
             "what": "542 Python problems with test suites large enough to fail "
                     "plausible-looking wrong answers"},
        ],
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="./eval-data")
    parser.add_argument("--languages", default=",".join(LANGUAGES),
                        help="two-letter codes, comma separated")
    parser.add_argument("--only", choices=["flores", "sib", "belebele", "coding"],
                        help="fetch just one set")
    arguments = parser.parse_args()

    chosen = [code.strip() for code in arguments.languages.split(",") if code.strip()]
    unknown = [code for code in chosen if code not in LANGUAGES]
    if unknown:
        print(f"unknown languages: {unknown}\nknown: {', '.join(LANGUAGES)}",
              file=sys.stderr)
        return 2
    codes = [LANGUAGES[code][0] for code in chosen]

    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(codes)} languages -> {out}")

    if arguments.only in (None, "flores"):
        get_flores(out, codes)
    if arguments.only in (None, "sib"):
        get_per_language(out, codes, "sib200", SIB_FILE, ".tsv")
    if arguments.only in (None, "belebele"):
        get_per_language(out, codes, "belebele", BELEBELE_FILE, ".jsonl")
    if arguments.only in (None, "coding"):
        get_coding(out)

    write_manifest(out, codes)
    print(f"\nDone. See {out}/MANIFEST.json for licences and citations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
