# Learnings — Toy Scorer Autoresearch

## After 10 experiments (baseline 0.7625 → 0.925 dev, 0.60 → 0.75 holdout)

### What worked
1. **Suffix stemming** (+7.5pp) — biggest single improvement. "indexes"→"index", "containerized"→"container" etc.
2. **Word-length weighting** (+3.75pp) — longer/rarer words are more specific. log(1+len) as IDF proxy.
3. **Acronym expansion** (+3.75pp) — NLP→"natural language processing" etc. Targeted but effective.

### What didn't work
- **BM25-style TF saturation** — no improvement on pairwise ranking (TF matters for absolute scoring, not comparison)
- **Bigram overlap bonus** — same accuracy as stemming alone
- **Density bonus** — hurt accuracy (0.7125). Ratio of query tokens in doc penalizes long docs.
- **Power-scaled coverage** — ties stay ties under monotonic transforms
- **Co-occurrence bonus** — the relevant docs that need help already match 2+ terms; bonus doesn't break ties
- **Character trigram overlap** — too noisy to discriminate between domain-relevant and domain-irrelevant matches

### Remaining hard cases
1. **Polysemy** — "index funds" vs "database indexing" (same stem, different domain). Would need IDF from a real corpus.
2. **Zero-overlap semantic** — "deforestation" has no lexical connection to "climate change". Needs embeddings or domain thesaurus.
3. **Domain-ambiguous words** — "container" (Docker vs shipping), "security" (crypto vs home). Need multi-word context, not single-token matching.

### Pattern observations
- Targeted lexical fixes (stemming, acronyms) give 3-8pp each
- Scoring formula tweaks (power scaling, density) give 0pp — the ranking structure is fixed by which tokens match
- The remaining ceiling is set by the absence of semantic knowledge, which keyword methods can't reach
