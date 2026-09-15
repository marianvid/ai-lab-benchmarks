#!/usr/bin/env python3
"""Create a deterministic, per-case blinded TTS listening pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path


MODELS = {
    "human": "libritts-ground-truth-en100-v1",
    "omnivoice": "libritts-omnivoice-en100-v1",
    "qwen": "libritts-qwen-en100-v1",
    "firered-base": "libritts-firered-base-en100-v1",
    "firered-instruct": "libritts-firered-instruct-en100-v1",
    "fish": "libritts-fish-en100-v1",
}


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Lab blind TTS listening evaluation</title>
<style>
:root{color-scheme:dark;background:#11141a;color:#edf1f7;font:16px system-ui,sans-serif}body{max-width:1200px;margin:auto;padding:28px}h1{margin-bottom:6px}.muted{color:#a8b0bd}.toolbar{position:sticky;top:0;background:#11141aee;padding:12px 0;z-index:3;border-bottom:1px solid #303744}button,select,input,textarea{font:inherit;background:#1b2029;color:#edf1f7;border:1px solid #465064;border-radius:6px;padding:6px}button{cursor:pointer;padding:9px 14px}.case{border:1px solid #303744;border-radius:12px;margin:22px 0;padding:18px;background:#161a21}.prompt{font-size:1.12rem;line-height:1.5;background:#0d1015;padding:14px;border-radius:8px}.reference{display:flex;gap:14px;align-items:center;margin:12px 0}.candidate{display:grid;grid-template-columns:70px minmax(240px,1fr) minmax(390px,1.5fr) 85px minmax(180px,1fr);gap:10px;align-items:center;padding:10px 0;border-top:1px solid #303744}.candidate label{font-size:.78rem;color:#a8b0bd;display:block}.scores{display:grid;grid-template-columns:repeat(4,minmax(85px,1fr));gap:8px}audio{width:100%}.slot{font-weight:700;font-size:1.15rem}.done{color:#55d98a}@media(max-width:900px){.candidate{grid-template-columns:55px 1fr}.scores{grid-column:1/-1;grid-template-columns:repeat(2,1fr)}.candidate>label,.candidate>textarea{grid-column:1/-1}}
</style></head><body>
<h1>Blind English TTS listening evaluation</h1>
<p class="muted">20 prompts × 6 anonymous candidates. The human recording is hidden among the five models and slot letters are shuffled independently for every prompt.</p>
<div class="toolbar"><span id="progress"></span> <button id="export">Export ratings JSON</button> <button id="clear">Clear saved ratings</button></div>
<div id="app"></div>
<script>const DATA=__DATA__;const KEY='ai-lab-tts-en-blind-v1';let state=JSON.parse(localStorage.getItem(KEY)||'{}');
const fields=[['text','Text fidelity'],['natural','Naturalness'],['voice','Voice match'],['usable','Editorial usability']];
function save(){localStorage.setItem(KEY,JSON.stringify(state));progress()}
function progress(){let n=0,total=DATA.cases.length*6*4;for(const c of DATA.cases)for(const s of c.candidates)for(const [f] of fields)if(state[c.id]?.[s.slot]?.[f])n++;document.querySelector('#progress').innerHTML=`<b class="done">${n}</b> / ${total} numeric ratings saved`}
function candidate(c,s){let wrap=document.createElement('div');wrap.className='candidate';wrap.innerHTML=`<div class="slot">${s.slot}</div><audio controls preload="none" src="${s.audio}"></audio><div class="scores"></div><label>Reject<br><input type="checkbox"></label><textarea rows="2" placeholder="Notes"></textarea>`;state[c.id]||={};state[c.id][s.slot]||={};let rec=state[c.id][s.slot];let scores=wrap.querySelector('.scores');for(const [f,label] of fields){let el=document.createElement('label');el.textContent=label;let select=document.createElement('select');select.innerHTML='<option value="">—</option>'+[1,2,3,4,5].map(x=>`<option>${x}</option>`).join('');select.value=rec[f]||'';select.onchange=()=>{rec[f]=select.value?Number(select.value):null;save()};el.append(select);scores.append(el)}let check=wrap.querySelector('input');check.checked=!!rec.reject;check.onchange=()=>{rec.reject=check.checked;save()};let note=wrap.querySelector('textarea');note.value=rec.notes||'';note.oninput=()=>{rec.notes=note.value;save()};return wrap}
for(const c of DATA.cases){let box=document.createElement('section');box.className='case';box.innerHTML=`<h2>${c.number}. Speaker ${c.speaker} · ${c.gender}</h2><div class="prompt">${c.text}</div><div class="reference"><b>Enrollment voice (different sentence)</b><audio controls preload="none" src="${c.reference_audio}"></audio></div>`;for(const s of c.candidates)box.append(candidate(c,s));document.querySelector('#app').append(box)}
document.querySelector('#export').onclick=()=>{let payload={schema_version:1,benchmark:DATA.benchmark,exported_at:new Date().toISOString(),ratings:state};let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}));a.download='tts-human-ratings.json';a.click();URL.revokeObjectURL(a.href)};
document.querySelector('#clear').onclick=()=>{if(confirm('Delete all locally saved ratings?')){state={};localStorage.removeItem(KEY);location.reload()}};progress();</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data, results, out = map(lambda value: Path(value).resolve(),
                             (args.data, args.results, args.out))
    manifest = json.loads((data / "manifest.json").read_text())
    speakers = {row["id"]: row for row in manifest["speakers"]}
    chosen = [row for row in manifest["cases"] if row["id"].endswith(("-02", "-07"))]
    assert len(chosen) == 20
    if out.exists():
        shutil.rmtree(out)
    (out / "audio").mkdir(parents=True)
    (out / "references").mkdir()
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    reference_hashes = {}
    for speaker, row in speakers.items():
        destination = out / "references" / f"{speaker}.wav"
        shutil.copy2(data / row["reference"]["audio"], destination)
        reference_hashes[speaker] = sha256(destination)
    public_cases, reveal = [], {}
    for number, case in enumerate(chosen, 1):
        case_out = out / "audio" / case["id"]
        case_out.mkdir()
        labels = list(MODELS)
        random.Random(int(hashlib.sha256(case["id"].encode()).hexdigest()[:16], 16)).shuffle(labels)
        candidates, mapping = [], {}
        for index, label in enumerate(labels):
            slot = chr(ord("A") + index)
            source = results / MODELS[label] / "audio" / f"{case['id']}.wav"
            destination = case_out / f"{slot}.wav"
            shutil.copy2(source, destination, follow_symlinks=True)
            candidates.append({"slot": slot, "audio": f"audio/{case['id']}/{slot}.wav",
                               "sha256": sha256(destination)})
            mapping[slot] = label
        public_cases.append({"number": number, "id": case["id"], "speaker": case["speaker"],
                             "gender": case["gender"], "text": case["text"],
                             "reference_audio": f"references/{case['speaker']}.wav",
                             "reference_sha256": reference_hashes[case["speaker"]],
                             "candidates": candidates})
        reveal[case["id"]] = mapping
    public = {"schema_version": 1, "benchmark": "libritts-en-blind-listening-v1",
              "selection": "cases 02 and 07 for each of 10 speakers",
              "scale": {"1": "unusable", "2": "poor", "3": "acceptable",
                        "4": "good", "5": "excellent"}, "cases": public_cases}
    (out / "manifest.json").write_text(json.dumps(public, indent=2) + "\n")
    (out / "private-reveal.json").write_text(json.dumps(reveal, indent=2) + "\n")
    (out / "index.html").write_text(HTML.replace("__DATA__", json.dumps(public)), encoding="utf-8")
    (out / "README.md").write_text(
        "# Private blind listening pack\n\nOpen `index.html` in a browser. Rate candidates before opening "
        "`private-reveal.json`. Ratings auto-save in the browser; use **Export ratings JSON** when done.\n\n"
        "The human LibriTTS target is hidden among five synthetic candidates. LibriTTS is CC BY 4.0. "
        "This private pack is not part of the public benchmark repository.\n", encoding="utf-8")
    print(json.dumps({"cases": len(public_cases), "candidates": len(public_cases) * 6,
                      "output": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
