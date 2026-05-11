---
title: Content Addressing for corpus_core — Plain sha256 vs CID vs JCS vs VC
date: 2026-05-11
tags: [content-addressing, hashing, jcs, ipfs, cid, identity, corpus-core]
status: complete
---

# Content Addressing for `corpus_core` — Decision Memo

**Decision target:** Should `corpus_core` use plain `sha256_hex(canonical_json(...))` (today's choice, matches phenome) or adopt a content-addressing standard?

## TL;DR — stay plain sha256, but document the CID encoding-equivalence and tighten the canonical-JSON spec

**Keep `sha256_hex(canonical_json(...))` as the on-disk and in-DB identity primitive.** It matches phenome's invariant, it has zero deps, and — this is the load-bearing fact — **a sha256 hex digest is a multihash and CID waiting to happen.** Wrapping `12 20 <32 bytes>` and base32-encoding it yields a valid CIDv1 with no rehashing. The "future-proof" path is a one-line `to_cidv1()` view, not a schema migration. We pay nothing now and lose nothing later.

Three concrete actions, none disruptive:
1. **Tighten the spec, not the bytes.** Document that our `canonical_json` is "RFC 8785-compatible for the value subset we use (no floats outside integers, no surrogate pairs, NFC strings)" — call out the divergences. Add a property test against `trailofbits/rfc8785.py` for that subset. Don't switch the implementation unless we add free floats to the schema.
2. **Pure-function CID view.** Add `corpus_core.identity.to_cidv1_b32(hex_digest) -> str` (10 lines, no deps beyond `base64`/`base32`/`multiformats-cid` optional). This is rederivable; not stored. If anyone asks for a CID, we have one.
3. **Don't adopt VC, Sigstore, or CBOR.** Each addresses a problem we don't have (third-party signature verification, transparency-log auditing, schema-agnostic compactness). They are tax with no current return; if the publishing use-case materializes, we adopt then.

For annotation IDs specifically: **content-addressed `sha256(canonical_json(stable_tuple))` is correct, not UUID5.** UUID5 uses MD5 internally (collision-broken since 2008) and truncates to 122 bits. A sha256-based deterministic ID is strictly stronger, costs nothing more, and is what `corpus_core` already does.

---

## Comparison — cost vs interop value at single-user, local-filesystem, multi-year scale

| Candidate | Cost to adopt now | Interop value (today) | Interop value (3-5y) | Verdict |
|---|---|---|---|---|
| **Plain `sha256_hex(canonical_json)`** | $0 (current) | Universal — every tool reads hex | Same; convertible to CID at any time | **KEEP** |
| **IPFS CID v1 / multihash / base32** | Low (~30 LoC encoder, one optional dep) | None — no consumer demands CIDs | Low — only if we federate to IPFS/Filecoin/dweb | **Add encoding view only** |
| **W3C VC Data Integrity (Ed25519/JWS)** | High — key management, JCS-strict canonicalization, JWS envelope | Zero (no verifier exists outside us) | Low — only if we publish signed claims to a verifier | **REJECT** |
| **Sigstore / Rekor transparency log** | High — OIDC, Fulcio cert, Rekor log entries | Zero (no consumer) | Maybe, if we publish a redistributable corpus | **REJECT now; revisit on publish** |
| **RFC 8785 / JCS (strict)** | Low-medium — swap `json.dumps(sort_keys=True)` for `rfc8785.py`; bytes may shift for floats/surrogates | Compat with JWS/VC/COSE downstream | Same — the *only* canonical-JSON spec with an IETF RFC | **Document compatibility; switch only if we add floats** |
| **CBOR canonical (RFC 8949 §4.2 / dCBOR)** | Medium — schema for binary, breaks DuckDB JSON projection | Zero (we have no CBOR consumers) | Low — niche outside COSE/IoT | **REJECT** |

The asymmetry that drives the verdict: **plain sha256 is one-way-convertible into every other addressing scheme without rehashing.** The reverse is not true. CID-first or VC-first means rewriting on every divergence. Sha256-first means we always have the option.

---

## RFC 8785 / JCS — specific recommendation

**Verdict: keep our `canonical_json`, document its JCS-compatible subset, add a property test. Do not adopt `rfc8785.py` as the implementation yet.**

What phenome's `canonical_json` does:
```python
json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

What this matches in JCS (RFC 8785):
- Compact separators (`,`, `:`) with no whitespace — yes
- Sort object members — yes
- UTF-8 byte output — yes
- Strings: pass-through of source string — yes for our NFC-normalized inputs

What this *diverges* from JCS:
- **Key sort order.** JCS sorts by UTF-16 code units; Python's `sort_keys=True` sorts by Unicode code point. **These differ only when keys contain non-BMP characters (surrogate pair range U+10000+).** Our keys are ASCII slot names, predicate ids, ISO dates, ontology codes. No divergence in practice.
- **Number serialization.** JCS mandates ES6 / V8 number-to-string (shortest round-trip, no trailing zeros, no `.0` for integers). Python's default `json.dumps` differs on edge cases (1.0 → "1.0" vs JCS "1"). The phenome canonicalize already short-circuits this — *floats are only kept if integer-valued, and rounding is upstream's job*. The schema deliberately avoids floats outside integers, which sidesteps the whole class.
- **String escaping.** JCS mandates a specific minimal-escape set; Python's defaults are similar but not byte-identical for control characters U+0000-U+001F. We don't store such characters in identity-bearing fields.

**Concrete action:**

1. Add a docstring section to `canonicalize.py`: "**JCS compatibility:** The output is byte-identical to RFC 8785 for the schema subset we use: NFC strings, ASCII keys, integers and integer-valued floats only, no control chars. The full JCS number serialization rules are not implemented — we forbid the inputs they cover."
2. Add a property test: for a fixed corpus of representative payloads, `canonical_json(x) == rfc8785.dumps(x)`. Pin `trailofbits/rfc8785.py` as a **test-only dev dep**, never a runtime dep. If the test ever fails because someone adds floats, the test is the conversation.
3. Do not swap implementations. Switching means rewriting every existing identity_key in phenome — irreversible churn for zero present benefit. The compat test gates the divergence; that's enough.

---

## Annotation IDs — content-addressing vs UUID5

For annotation IDs that include subjective scope (`actor_id`, prompt hash, asserted-at date), **content-addressing is the right choice and we already do it.** The annotation's identity is exactly the tuple `(source_hash, instrument_id, prompt_hash, scope, asserted_at_day)` — that *is* its identity. `sha256(canonical_json(tuple))` is the natural key.

UUID5 alternative analysis:
- **Cryptographic weakness.** UUID5 uses SHA-1 (deprecated since 2017 by NIST); UUID3 uses MD5 (broken 2008). Truncated to 122 bits of entropy via version/variant bit pinning.
- **Namespace ceremony.** Requires picking a namespace UUID; everyone invents their own → no actual interop benefit.
- **No upgrade path.** UUID5 → sha256 means rewriting all IDs. sha256 → CID is a view.

**The only legitimate UUID use-case in corpus_core: ephemeral session/run identifiers** (where collision-resistance over a few days at one user is enough and the value is *not* a derived assertion). Use `uuid7` (time-ordered, better than uuid4 for SQLite primary-key locality) — never `uuid5` for content identity.

---

## What we'd lose if we don't adopt — actually nothing in 2026

Surveyed publishing/repository targets for 2026-era CID adoption:
- **Zenodo:** verified — issues DOIs, no CIDs. Their docs reserve DOI as the canonical PID. No CID adoption planned in their public roadmap.
- **Hugging Face Datasets:** verified — uses repo + git-LFS-style content hashing internally, no CID. Third-party IPFS bridges exist (`endomorphosis/ipfs_datasets_py`) but are community projects, not native HF.
- **Semantic Scholar:** verified — `CorpusID` is a sequential integer assigned by S2's ingestion pipeline. Not content-derived. Not changing.
- **Crossref / DataCite:** DOI-only; no CID.
- **arXiv:** sequential `arXiv:YYMM.NNNNN`, no content addressing.

The "publishing tools will want CIDs" hypothesis is unsupported. The actual landscape is **DOI-monoculture for academic** and **repo-name-based for ML datasets**. CIDs remain a dweb/Filecoin niche. Our existing sha256 hex digests are universally readable as opaque IDs by any of these systems and convertible into CIDs the moment that changes.

The one real loss-if-we-don't-adopt scenario: if we ever want to **publish the corpus as content-addressed federated data** (gateway-pinnable, dweb-discoverable). That is a publishing decision, not an identity decision. The on-disk hex digest does not need to change for that to happen — we generate CIDs as an export view.

---

## Sources

- RFC 8785 — JSON Canonicalization Scheme (https://www.rfc-editor.org/rfc/rfc8785) — authoritative spec; verified `verify_claim` 1.0 confidence.
- Python json sort_keys divergence — CPython issue #135623 (https://github.com/python/cpython/issues/135623), #70417 number serialization compat — verified 0.9 confidence.
- trailofbits/rfc8785.py (https://github.com/trailofbits/rfc8785) — strict reference impl, pin as dev-dep for property tests.
- IPFS multiformats/cid (https://github.com/multiformats/cid) and multiformats/multihash — verified that sha256-hex → CIDv1-base32 is a pure encoding transformation; no rehashing. 1.0 confidence.
- Zenodo DOI docs (https://help.zenodo.org/docs/deposit/describe-records/reserve-doi) — confirms DOI-only PID policy; no CID adoption.
- Hugging Face datasets cloud-storage docs (https://huggingface.co/docs/datasets/filesystems) — no native CID; third-party bridges only.
- Semantic Scholar Open Data Platform (https://api.semanticscholar.org/CorpusID:256194545) — CorpusID is sequential integer; verified 1.0 confidence.
- W3C VC Data Integrity 1.0 — out of scope here (no verifier consumer); rejection rationale: high adoption cost for zero current interop value.
- NIST SP 800-131A — SHA-1 deprecation; UUID5 is built on SHA-1 and is unsuitable for new content-identity work.
- Internal: `/Users/alien/Projects/phenome/src/phenome/identity/canonicalize.py` — current implementation reviewed; matches JCS for the schema subset used.
- Internal: `research/prior-art-2026-05-11/02-provenance-attestation-patterns.md` (round 1) — rejected RO-Crate packaging, Sigstore, in-toto for similar single-user reasons; consistent with this verdict.

<!-- knowledge-index
generated: 2026-05-11T07:45:38Z
hash: 8c86d95e8081

title: Content Addressing for corpus_core — Plain sha256 vs CID vs JCS vs VC
status: complete
tags: content-addressing, hashing, jcs, ipfs, cid, identity, corpus-core
cross_refs: research/prior-art-2026-05-11/02-provenance-attestation-patterns.md

end-knowledge-index -->
