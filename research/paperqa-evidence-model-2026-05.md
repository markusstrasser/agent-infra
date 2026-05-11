---
title: PaperQA2 evidence model — what to copy for ~/Projects/papers/
date: 2026-05-11
topic: citance / evidence-passage / claim-source linking
scope: paper-qa OSS (main branch as of 2026-05), WikiCrow & ContraCrow configs, edison-client-docs
---

# PaperQA2 evidence model — deep dive

Goal: understand how paper-qa links a synthesized claim back to a specific passage so we can copy the good parts into a personal-scale shared papers store.

## Core data model (verified from source)

Defined in `src/paperqa/types.py`. Pydantic v2 models, all inherit Pydantic `BaseModel`; `Doc`/`Text` extend `Embeddable` (from the `lmi` package, not paper-qa itself). [B1: github.com/Future-House/paper-qa/blob/main/src/paperqa/types.py]

```python
class Doc(Embeddable):
    docname: str
    dockey: DocKey                  # unique ID
    citation: str                   # rendered citation string
    content_hash: str | None
    fields_to_overwrite_from_metadata: set[str]

class Text(Embeddable):
    text: str                       # raw chunk text
    name: str                       # e.g. "Smith2023 pages 3-5"  <-- key insight
    media: list[ParsedMedia]        # images on those pages
    doc: Doc | DocDetails

class Context(BaseModel):
    id: str                         # auto: "pqac-<8hex>"
    context: str                    # LLM-generated summary wrt question (NOT raw text)
    question: str | None
    text: Text                      # full Text object embedded by reference
    score: int                      # 0-10 relevance, LLM-assigned

class PQASession(BaseModel):
    id: UUID
    question: str
    answer: str
    raw_answer: str                 # LLM output with inline (pqac-...) keys
    formatted_answer: str           # prettified, references substituted
    contexts: list[Context]         # all evidence considered
    references: str                 # rendered bibliography
    config_md5: str | None          # frozen — reproducibility hash
    tool_history: list[list[str]]
    cost: float
    token_counts: dict[str, list[int]]
```

**The linkage primitive is `Context.id` (the `pqac-<hex>` key).** The LLM is prompted to cite passages as `(pqac-d79ef6fa)` or `(pqac-d79ef6fa, pqac-0f650d59)` inline in `raw_answer`; downstream rendering substitutes these to MLA references. Constraints prohibit `;` separators, conjunctions, and `"pages pqac-..."`-style prefixes. [B1: src/paperqa/prompts.py via README]

## Where page numbers live — IMPORTANT

There is **no structured page field** on `Text` or `Context`. Page info is encoded **as a string inside `Text.name`** by the PDF reader: [A1: src/paperqa/readers.py `_make_chunk`]

```python
name = "-".join([lower_page, upper_page])
return Text(text=text, name=f"{doc.docname} pages {name}", media=media, doc=doc)
```

So a chunk is named `"Qian2011Neural pages 1-2"`. Single-page chunks are `"docname pages 3-3"`. Code chunks get `"docname lines 12-47"`; plain text gets `"docname chunk 5"`. This is the format that surfaces in user-facing citations like `(Qian2011Neural pages 1-2)`. [B1: README example]

No character offsets, no PDF bbox, no Y-coordinate, no figure/table anchors. If you want highlight-on-PDF later, this model can't support it.

## Persistence

- `Docs` (the corpus container, not shown above) supports **pickle only** per README. No JSON schema, no SQLite, no save method on `PQASession`. [B1: README]
- `Doc.to_csv()` exists for bibliography export. `ParsedMedia.save()` writes image bytes.
- `config_md5` on `PQASession` is frozen to let you reproduce a session if you have the same settings + corpus pickle.

This is the weakest part of the stack for our use case. Pickle is brittle across paper-qa versions, opaque to grep, and unfit for multi-process or multi-host sharing.

## ContraCrow contradiction detection

Implemented as a **config preset**, not a separate schema. [A1: src/paperqa/configs/contracrow.json]

- User query is a *claim*; system retrieves evidence and asks the LLM to label it.
- Output is XML: `<response><reasoning>...</reasoning><label>...</label></response>`.
- 11-level ordinal label: `explicit contradiction` → `nuanced contradiction` → `possibly contradiction` → `lack of evidence` → ... → `explicit agreement`.
- 7000-char chunks (vs default ~3000), 250 overlap, temperature 0.
- **No graph edges, no contradiction store.** Result is just the `PQASession.formatted_answer` string with the XML label. Caller must parse + persist themselves.

## WikiCrow

Also a config preset. [A1: src/paperqa/configs/wikicrow.json] Caps evidence at 25 contexts, cites max 12 in final article, requires Wikipedia tone, instructs "Only cite from the context below," and reserves an "Overview" section header. Same `(pqac-...)` citation mechanism — no special multi-paper synthesis primitive beyond "more contexts, longer answer prompt."

## What to copy

1. **Stable per-chunk ID** (`pqac-<8hex>` style) — short, citable inline, decoupled from doc/page so renames don't break references. Hash the chunk text content.
2. **Three-layer model: Doc / Text / Context.** Keep `Context.summary` distinct from `Text.text` — the summary is what the LLM saw, the raw chunk is what's auditable. This is the single best idea here.
3. **Ordinal stance labels** for contradiction (their 11-level scale is overkill — 5 levels: contradicts/qualifies/neutral/supports/strongly-supports is enough). Store as edge metadata.
4. **`config_md5` frozen on the session** — cheap reproducibility token.
5. **`raw_answer` vs `formatted_answer` split** — keep the raw inline-citation form as the source of truth, render to display formats on demand.

## What to avoid

1. **Page numbers as strings inside `name`.** Make page a structured field (`page_start: int`, `page_end: int`, plus optional `char_offset` and `bbox`) from day one — paper-qa's choice forecloses highlight-on-PDF.
2. **Pickle-only persistence.** Use SQLite + JSON columns or duckdb; you want grep-able, multi-process-safe, schema-versioned storage. Your citance/graph layer needs this anyway.
3. **Contradiction as ephemeral XML.** Persist `(claim_a_chunk_id, claim_b_chunk_id, stance, reasoning, asserter_model, asserted_at)` as edges in the graph layer. paper-qa throws this away after each session.
4. **`Context.context` summary as the only retained form.** Always also store the verbatim source span — the summary is lossy and model-version-dependent.
5. **Sentence-end-only citation.** Their prompt forces citations at sentence boundaries; for a knowledge graph, you want span-level claim → span-level evidence, not sentence → chunk. Allow finer grain.

## Edison / PaperQA3

`edison-client-docs` is a thin user guide; says "built with PaperQA3" and references `formatted_answer` + cited responses but exposes no internal schema. PaperQA3 is closed-source. Treat PaperQA2 OSS as the reference architecture; no leaked details suggest PaperQA3 changed the Context primitive. [C2: edison-client-docs README]

## Provenance grades

- A1: read directly from paper-qa main-branch source files via raw.githubusercontent.com (types.py, readers.py, configs)
- B1: paper-qa README (FutureHouse-authored, current)
- C2: edison-client-docs (vendor marketing-ish, low detail)
- Not consulted: arXiv PaperQA2 paper (Skarlinski et al.), Nature WikiCrow paper — schema-level questions answered from code which supersedes prose

<!-- knowledge-index
generated: 2026-05-11T04:18:19Z
hash: 202665ee9b36

title: PaperQA2 evidence model — what to copy for ~/Projects/papers/
sources: 8
  B1: github.com/Future-House/paper-qa/blob/main/src/paperqa/types.py
  B1: src/paperqa/prompts.py via README
  A1: src/paperqa/readers.py `_make_chunk`
  B1: README example
  B1: README
  A1: src/paperqa/configs/contracrow.json
  A1: src/paperqa/configs/wikicrow.json
  C2: edison-client-docs README

end-knowledge-index -->
