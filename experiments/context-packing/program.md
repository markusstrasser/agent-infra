# Context Packing RSI Program

Optimize `packer.py`, a small policy that selects context IDs for a prompt
under a budget. The current cases are a seed mix:

- gold-ish failure contexts where missing a surface would be bad
- silver replay-style contexts derived from common project work shapes

Do not edit `cases.json` or `eval.py`. Kept patches must pass the locked dev +
holdout suite and should improve recall without adding broad, noisy context.
