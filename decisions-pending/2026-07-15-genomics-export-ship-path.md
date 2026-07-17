# Genomics: kill certificate-maze / unblock real ship path

**Boundary:** shared (genomics control-plane) + irreversible-ish (changes what "SECURE" means)
**Recommendation:** Stop treating `just donor-shipping-readiness` as the ship gate. Make **`just donor-export-authority <sample>`** the only path that can flip shipping authorization; either (A) wire the legacy readiness screen to *consume* principal plan/capture/authorization records so `export_plan_binding` can pass, **or (B)** delete/relabel the legacy screen as diagnostics-only and ban attestation churn as a substitute for ship.
**Dissent / risk:** (A) risks laundering if the screen can pass without sink-admitted bytes; (B) breaks muscle memory in Codex/Claude sessions that still call the legacy recipe. Drift observe (6 sessions / 21d) shows ~78% of recent commits as attestation/self-verification while `axis_export_plan_binding` stays fail-closed and **zero samples ship**.
**Open question for you:** Prefer **wire (A)** or **relabel/kill (B)** for the legacy screen?
**Reversible?** Partial — wiring is reversible; deleting the recipe needs a one-line redirect. Wrong choice costs more attestation churn, not data loss.
**Evidence:**
- observe drift `artifacts/observe/2026-07-15-2152/drift/drift-digest.md` promotable #1
- `genomics/scripts/donor_shipping_readiness.py` (explicit: does not consume principal plan/capture; `export_plan_binding` fail-closed → `NOT_SECURE`)
- `genomics/CLAUDE.md` shipping-readiness vs `donor-export-authority` split
- architecture observe: shared-checkout collisions amplify the maze (peers dirty the tree while binding stays stubbed)

**Next if approved:** genomics session implements A or B with a regression test that a sample with principal records can reach SECURE, and a sample without cannot.
