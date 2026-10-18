#!/usr/bin/env python3
"""Collect whole Wikipedia articles, for measuring throughput on long prompts.

The evaluation sets in this suite are sentences and short passages. Real bulk
work usually sends a document, and prompt length changes how an engine behaves:
the prompt is what fills the key-value cache, and the cache is what limits how
many requests can be in flight at once.

Wikipedia article text is Creative Commons Attribution-ShareAlike 4.0, so it can
be collected and redistributed with attribution. This gathers articles in a
fixed length band, in several languages, for `bench_longform.py` to send.

**No labels are involved.** The articles are input volume, not ground truth. The
answers are never marked.

Collection is in two passes, because most random articles are stubs and fetching
their text would be wasted traffic:

1. ask for a batch of random articles and read only their wikitext size, which
   is cheap, and keep the plausible ones;
2. fetch the plain text of those, and keep the ones that land in the band.

Every kept article records its page id, revision id and URL, so each is
attributable and the exact text can be recovered later even if it changes.

    python3 fetch_wikipedia.py --out eval-data/wikipedia_articles.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Wikipedia asks automated clients to identify themselves and say how to be
# contacted. https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = ("ai-lab-benchmarks/1.0 (research corpus builder; "
              "https://github.com/marianvid/ai-lab-benchmarks)")

# Characters of plain text. Long enough to matter for the cache, short enough
# that a run finishes.
MIN_CHARS = 2165
MAX_CHARS = 5240

# Wikitext carries markup and templates that plain text does not, so a page is
# always larger in wikitext. These bounds only decide what is worth fetching.
MIN_WIKITEXT = 3000
MAX_WIKITEXT = 60000

BATCH = 50              # random pages per request
PAUSE_S = 0.4           # between requests, to stay a polite client
RETRY_PAUSE_S = 3       # after a failed request

# A page is prose when at least PROSE_LINES of its lines are longer than
# PROSE_LINE_CHARS; anything less is a list or a table.
PROSE_LINE_CHARS = 120
PROSE_LINES = 3

# Rounds in a row that add nothing before a language is given up on.
GIVE_UP_ROUNDS = 25


def api(lang: str, params: dict) -> dict:
    """One call to a Wikipedia's API (refused when its servers lag); an API error raises."""
    query = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"{lang}: {payload['error'].get('info', payload['error'])}")
    return payload


def candidates(lang: str) -> list[dict]:
    """A batch of random articles, filtered to a plausible size by wikitext."""
    payload = api(lang, {"action": "query", "generator": "random",
                         "grnnamespace": 0, "grnlimit": BATCH,
                         "prop": "info", "inprop": "url"})
    pages = payload.get("query", {}).get("pages", [])
    return [page for page in pages
            if MIN_WIKITEXT <= page.get("length", 0) <= MAX_WIKITEXT]


def with_text(lang: str, pages: list[dict]) -> list[dict]:
    """Fetch the plain text of a set of pages, in one request."""
    if not pages:
        return []
    payload = api(lang, {"action": "query",
                         "pageids": "|".join(str(p["pageid"]) for p in pages),
                         "prop": "extracts|revisions", "explaintext": 1,
                         "exsectionformat": "plain", "rvprop": "ids"})
    return payload.get("query", {}).get("pages", [])


def usable(page: dict) -> str | None:
    """The article's text, or None if this page should not be in the set."""
    text = (page.get("extract") or "").strip()
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        return None
    # A disambiguation page is a list of links with almost no prose, and a page
    # that is mostly one-line entries is a table in disguise. Either would make
    # the prompts shorter and more repetitive than real articles.
    lines = [line for line in text.splitlines() if line.strip()]
    if len([line for line in lines if len(line) > PROSE_LINE_CHARS]) < PROSE_LINES:
        return None
    return text


def one_round(lang: str) -> tuple[list[dict] | None, int]:
    """One candidate batch with its text, and how many requests that took.

    The pages are None when a request failed; the caller tries again.
    """
    try:
        batch = candidates(lang)
        time.sleep(PAUSE_S)
        pages = with_text(lang, batch)
        time.sleep(PAUSE_S)
    except (urllib.error.URLError, RuntimeError, TimeoutError) as error:
        print(f"  {lang}: {error} — retrying", file=sys.stderr)
        time.sleep(RETRY_PAUSE_S)
        return None, 1
    return pages, 2


def record(lang: str, page: dict, text: str) -> dict:
    """One kept article, with what is needed to attribute and recover it."""
    revisions = page.get("revisions") or [{}]
    return {"lang": lang, "pageid": page["pageid"],
            "revid": revisions[0].get("revid"),
            "title": page["title"],
            "url": f"https://{lang}.wikipedia.org/?curid={page['pageid']}",
            "chars": len(text), "text": text}


class Collection:
    """The articles kept so far in one language."""

    def __init__(self, lang: str, wanted: int) -> None:
        self.lang = lang
        self.wanted = wanted
        self.kept: list[dict] = []
        self.seen: set[int] = set()

    def add(self, pages: list[dict]) -> bool:
        """Keep the usable pages not seen before; True if any were kept."""
        before = len(self.kept)
        for page in pages:
            if len(self.kept) >= self.wanted or page["pageid"] in self.seen:
                continue
            text = usable(page)
            if text is None:
                continue
            self.seen.add(page["pageid"])
            self.kept.append(record(self.lang, page, text))
        return len(self.kept) > before


def collect(lang: str, wanted: int, budget: int) -> list[dict]:
    """Random articles in one language until `wanted` are kept or `budget` calls are spent."""
    collection = Collection(lang, wanted)
    requests_made = 0
    empty_rounds = 0
    while len(collection.kept) < wanted and requests_made < budget:
        pages, spent = one_round(lang)
        requests_made += spent
        if pages is None:
            continue
        empty_rounds = 0 if collection.add(pages) else empty_rounds + 1
        if empty_rounds >= GIVE_UP_ROUNDS:
            print(f"  {lang}: giving up at {len(collection.kept)}/{wanted} — this "
                  f"edition has few articles in the band", file=sys.stderr)
            break
        print(f"  {lang}: {len(collection.kept)}/{wanted}", end="\r", file=sys.stderr)
    print(f"  {lang}: {len(collection.kept)}/{wanted} in {requests_made} requests",
          file=sys.stderr)
    return collection.kept


def main() -> int:
    """Collect the articles for every language and write them, with their licence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", default="ru,uk,lt,pl,ro,en")
    parser.add_argument("--per-language", type=int, default=100)
    parser.add_argument("--budget", type=int, default=900,
                        help="maximum API requests per language")
    parser.add_argument("--out", default="wikipedia_articles.jsonl")
    arguments = parser.parse_args()

    languages = [code.strip() for code in arguments.languages.split(",") if code.strip()]
    everything: list[dict] = []
    for lang in languages:
        everything.extend(collect(lang, arguments.per_language, arguments.budget))

    with open(arguments.out, "w", encoding="utf-8") as handle:
        for row in everything:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for row in everything:
        counts[row["lang"]] = counts.get(row["lang"], 0) + 1
    print(f"\n{len(everything)} articles -> {arguments.out}")
    for lang in languages:
        print(f"  {lang}: {counts.get(lang, 0)}")
    print("\nText is CC BY-SA 4.0 from Wikipedia; each row carries its page id, "
          "revision id and URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
