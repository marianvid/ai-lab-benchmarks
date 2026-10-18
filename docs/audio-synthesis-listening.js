const sets = [
  {title: "Qwen3-TTS 1.7B VoiceDesign — accents, emotion and characters", kind: "tts", slug: "qwen-voicedesign", result: "qwen-voicedesign/raw.json"},
  {title: "Qwen3-TTS 1.7B CustomVoice — Aiden and Ryan", kind: "tts", slug: "qwen-customvoice", result: "qwen-customvoice/raw.json"},
  {title: "Chatterbox Turbo — natural English and paralinguistic events", kind: "tts", slug: "chatterbox-turbo", result: "chatterbox-turbo/raw.json"},
  {title: "Dia2 2B — experimental two-speaker dialogue", kind: "tts", slug: "dia2-2b", result: "dia2-2b/raw.json"},
  {title: "TangoFlux — experimental sound effects (research/non-commercial licence)", kind: "sfx", slug: "tangoflux", result: "tangoflux/raw.json"}
];

function element(name, text, className) {
  const node = document.createElement(name);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

async function renderSet(spec) {
  const content = document.querySelector("#content");
  const section = document.createElement("section");
  section.append(element("h2", spec.title));
  const grid = element("div", undefined, "grid");
  section.append(grid);
  content.append(section);
  try {
    const root = spec.kind === "tts" ? "../results/audio-synthesis/" : "../results/sound-effects/";
    const response = await fetch(root + spec.result);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const data = await response.json();
    for (const row of data.cases.filter(item => item.ok)) {
      const card = document.createElement("article");
      card.append(element("h3", row.id));
      const details = [row.category, row.speaker, row.audio_duration_s && `${row.audio_duration_s}s`].filter(Boolean).join(" · ");
      card.append(element("div", details, "meta"));
      const input = row.prompt || row.script || row.text;
      card.append(element("div", input, "input"));
      if (row.instruction) card.append(element("div", `Voice instruction: ${row.instruction}`, "input"));
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = spec.kind === "tts"
        ? `../samples/audio-synthesis/${spec.slug}/${row.id}.wav`
        : `../samples/sound-effects/${spec.slug}/${row.id}.wav`;
      card.append(audio);
      grid.append(card);
    }
  } catch (error) {
    grid.append(element("p", `Could not load this set: ${error.message}`, "error"));
  }
}

sets.reduce((chain, spec) => chain.then(() => renderSet(spec)), Promise.resolve());
