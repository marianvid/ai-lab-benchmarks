# A bug in vLLM 0.27.1 — Gemma-4 will not load

**Affects vLLM 0.27.1 only. The nightly build fixes it.** This machine now runs
`0.26.1rc1.dev949`, with no patch applied, and Gemma-4 loads and runs the whole
benchmark on it. The page is kept for the diagnosis, not because anything here
still needs doing.

Patch in `harness/fix_gemma4.py`, useful only if pinned to 0.27.1. It edits a
file inside the installed package, so any upgrade silently reverts it.

Symptom resembles a corrupt checkpoint; cause is a config attribute change in
transformers >= 5.15.

## Symptom

Any Gemma-4 model in a native quantised format fails to start on vLLM 0.27.1.
Both variants tested fail, from different publishers and different quantisation
toolchains, so it is not a bad checkpoint:

- `nvidia/Gemma-4-26B-A4B-NVFP4` — modelopt, MoE
- `RedHatAI/gemma-4-12B-it-NVFP4` — compressed-tensors, dense

Two errors appear, one after the other. The second only becomes visible once the
first is worked around.

## Defect 1 — an exception caught by the wrong name

```
transformers.integrations.heterogeneity.configuration_utils.
AmbiguousGlobalPerLayerAttributeError: 'head_dim' is a per-layer attribute...
```

Raised from `vllm/transformers_utils/model_arch_config_convertor.py:608`:

```python
head_dim = getattr(self.hf_text_config, "head_dim", 0)
```

The default argument shows the author expected the attribute to be *absent* on
some configs. Transformers 5.15 does not report it absent; it raises. And
`AmbiguousGlobalPerLayerAttributeError` subclasses **`RuntimeError`, not
`AttributeError`**, so `getattr`'s default does not catch it and startup dies.

**Workaround.** The exception message names its own escape hatch. Add one key to
the model's `config.json`, inside `text_config`:

```json
"allow_global_per_layer_attribute_access": true
```

`benchmark/harness/patch_gemma_cfg.py` does this and keeps a `.orig` backup. This is safe
here: vLLM wants the global value in order to size buffers for the largest case,
which is exactly the use the warning permits.

## Defect 2 — layers built with the wrong dimensions

Getting past defect 1 reveals the real problem:

```
AssertionError: Attempted to load weight (torch.Size([512]))
                into parameter (torch.Size([256]))
```

Gemma-4 mixes two attention shapes:

| Layer type | Count | `head_dim` | key-value heads |
|---|---:|---:|---:|
| sliding attention | 25 | 256 | 8 |
| full attention | 5 | **512** | **2** |

Older transformers published the second set under the names `global_head_dim`
and `num_global_key_value_heads`, and `vllm/model_executor/models/gemma4.py`
reads exactly those names:

```python
if self.is_full_attention:
    head_dim = getattr(config, "global_head_dim", config.head_dim)
else:
    head_dim = config.head_dim
```

**Transformers 5.15 removed both names** and publishes the authoritative values
per layer, in `config.per_layer_config[i]`. So `getattr` finds nothing, falls
back to the sliding-layer value, and every one of the 30 layers is built with
head_dim 256 and 8 key-value heads. Loading then fails on the first
full-attention layer.

Instrumented output confirming it — `global_head_dim` is `None` for all layers,
including the ones marked `full_attention`:

```
[DBG] layer=5  type=full_attention    chosen=256 cfg.head_dim=256 cfg.global_head_dim=None
[DBG] layer=11 type=full_attention    chosen=256 cfg.head_dim=256 cfg.global_head_dim=None
[DBG] layer=17 type=full_attention    chosen=256 cfg.head_dim=256 cfg.global_head_dim=None
```

## The checkpoint is fine

Before blaming vLLM, the safetensors headers were read directly and compared
against the config, layer by layer: **25 layers at 256, 5 at 512, zero
mismatches.** What transformers exposes also matches:

```
per_layer_config head_dim            {256: 25, 512: 5}
per_layer_config num_key_value_heads {8: 25, 2: 5}
```

## The patch

`benchmark/harness/fix_gemma4.py`. It prefers the per-layer value where transformers
provides one and keeps the old lookup as a fallback, so it is safe on older
transformers too. Two blocks changed in `gemma4.py`:

```python
_per_layer = getattr(config, "per_layer_config", None)
_lc = (_per_layer[layer_idx]
       if _per_layer is not None and layer_idx < len(_per_layer) else None)

if _lc is not None and getattr(_lc, "head_dim", None):
    head_dim = _lc.head_dim
elif self.is_full_attention:
    head_dim = getattr(config, "global_head_dim", config.head_dim)
else:
    head_dim = config.head_dim
```

and the same shape for `num_kv_heads`, reading `_lc.num_key_value_heads`.

Applied to
`/opt/ai/vllm/.venv/lib/python3.12/site-packages/vllm/model_executor/models/gemma4.py`,
with the pristine file kept as `gemma4.py.orig`.
