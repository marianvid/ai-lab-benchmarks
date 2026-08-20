# Tokenizer cost by language

How many [tokens](glossary.md#token) the same content costs in each
language.

This is not a quality measurement and needs no GPU. It counts the
same 200 FLORES sentences — identical content in every language —
with `gemma-4-26b-a4b`'s tokenizer.

| Language | Script | Characters per token | Tokens vs English |
|---|---|---:|---:|
| lt | Latin | 2.86 | **1.66×** |
| th | Thai | 2.84 | **1.65×** |
| uk | Cyrillic | 2.99 | **1.64×** |
| ro | Latin | 3.47 | **1.57×** |
| pl | Latin | 3.36 | **1.52×** |
| ta | Tamil | 3.77 | **1.49×** |
| ar | Arabic | 2.86 | **1.48×** |
| fr | Latin | 4.01 | **1.41×** |
| ru | Cyrillic | 3.72 | **1.40×** |
| ko | Hangul | 1.74 | **1.39×** |
| vi | Latin | 3.68 | **1.37×** |
| tr | Latin | 3.63 | **1.36×** |
| de | Latin | 4.19 | **1.34×** |
| hi | Devanagari | 3.61 | **1.31×** |
| es | Latin | 4.39 | **1.29×** |
| pt | Latin | 4.17 | **1.26×** |
| ja | Japanese | 1.69 | **1.24×** |
| bn | Bengali | 3.89 | **1.23×** |
| zh | Han | 1.45 | **1.12×** |
| en | Latin | 4.79 | **1.00×** |

**Reading the last column.** 1.50× means the same text costs half
again as many tokens as in English: a context window holds two
thirds as much of it, a request takes half again as long to read,
and a hosted model charges half again as much.

**The writing system does not predict the cost.** Chinese, in Han
characters, is the cheapest language here after English. The most
expensive is lt, written in Latin — the same
alphabet as English.

What decides it is how much of that language the tokenizer was built
from. One trained mostly on English and Chinese text holds whole
Chinese words as single tokens and cuts Lithuanian into fragments.

**The practical consequence.** A context window sized against
English documents holds about 60% as much lt. Size it on the most expensive language you will
actually send, or requests will be rejected for length in a way that
looks like a model fault.
