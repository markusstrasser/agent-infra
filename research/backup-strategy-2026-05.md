# macOS Backup Strategy — Decision Memo (2026-05)

**Subject:** MacBook Pro M3 Pro power-user — true 3-2-1 backup with versioning + offsite encryption
**Date:** 2026-05-30 · **Status:** COMPLETE
**Author:** researcher agent · all pricing/feature claims web-verified May 2026 (see Source Grades)

---

## TL;DR — Top Recommendation

**Run a two-tier hybrid: keep Time Machine to the 2 TB external for versioning + the only real Apple-Silicon bare-metal path, and add `restic` → Backblaze B2 (S3 API) for the encrypted, always-on offsite copy. Schedule restic via launchd, granting Full Disk Access to the shell interpreter that runs it. ~$2–4/month.**

This is the lowest-maintenance setup that actually achieves 3-2-1 *and* solves the two macOS traps that quietly break naive CLI backups: the TCC/Full-Disk-Access wall and the sealed-system-volume restore limitation. Time Machine covers "oops I deleted a file / my Mac died" with near-zero effort; restic→B2 covers "my house burned down / external was unplugged" with strong client-side encryption you control. The external being removable is fine — it makes the *offsite* tier the load-bearing one, which is exactly where restic→B2 sits.

---

## Scope & Constraints

- **Machine:** MacBook Pro M3 Pro, 18 GB RAM, 512 GB SSD (~370 GB used), Apple Silicon, macOS Sequoia/Tahoe era.
- **External:** 2 TB PNY USB SSD, ~1.3 TB free, **REMOVABLE** (not always attached).
- **Already offsite:** code → GitHub · ~47 GB media → Google Drive · Desktop & Documents → iCloud (D&D-in-iCloud ON).
- **Must encrypt at rest + offsite:** SSH/GPG/AWS keys, API tokens, **medical PHI (WGS data + medical DuckDB)**, Signal history.
- **Today:** Time Machine (considering dropping — local APFS snapshots ate the disk). Has a bash system-config-capture script (brew manifest/dotfiles/prefs) — **NOT a data backup**, it's a rebuild accelerator.
- **Profile:** heavy CLI / many AI agents, comfortable with restic/borg, **wants low ongoing maintenance**.

## Goals

3-2-1 (3 copies, 2 media, 1 offsite) · versioned point-in-time restore · encryption at rest AND offsite · reliable restore · reasonable cost. Bare-metal a plus, not required (code/media/docs already in git/gdrive/iCloud).

---

## The four macOS gotchas (these decide the design)

### 1. TCC / Full Disk Access — the silent killer of unattended CLI backups
macOS's TCC (Transparency, Consent & Control) layer silently denies reads to protected locations — `~/Library` app data, **Messages/Signal history**, Mail, Photos, Calendars, and Time Machine backups — for any process that hasn't been granted **Full Disk Access (FDA)**. A backup that "succeeds" can be **silently missing your Signal DB and app data** with no error in the common case.

- **Interactive `restic` from Terminal** inherits Terminal's (or iTerm's) FDA grant if you've granted it — works.
- **`restic` from `launchd`** does **not** inherit anything. You must grant FDA explicitly. **Critical detail:** when launchd runs a *shell script* that calls restic, the process that touches the files is the **shell interpreter**, not the `restic` binary. So you grant FDA to **`/bin/bash`** (or `/bin/zsh`) — granting it to the `restic` binary alone does **not** work for a script-driven job, and adding a bare binary to the FDA pane is unreliable on modern macOS. *(Verified across two independent practitioner write-ups; see Source Grades.)*
  - **Security tradeoff (flag this):** granting FDA to `/bin/bash` means *anything* that bash runs gets full-disk reads. Acceptable on a single-user laptop, but note it. A tighter alternative is a tiny compiled wrapper (Swift) granted FDA — more correct, but more maintenance. For this user, FDA-on-shell is the right cost/benefit.
- **Time Machine is the exception:** its backup helper (`backupd`) runs with Apple's TCC permissions effectively pre-granted — it never appears in the FDA pane and the user never grants it. *(Operationally certain; the underlying mechanism — "special private entitlement" vs. Apple-signed-system-daemon handling — is contested. Don't over-claim the mechanism; the user-facing fact "TM needs no FDA setup, third-party tools do" is what matters.)*

**Implication:** any restic/borg/kopia job under launchd needs the FDA-on-shell step, or it under-backs-up. This is the #1 reason "I set up restic and thought I was covered" fails on Mac.

### 2. APFS local snapshots — the disk-eating behavior the user already hit
Time Machine creates **local APFS snapshots** hourly and keeps them ~24 h (plus more when the destination is unavailable — exactly the removable-external case). On a 512 GB SSD with 370 GB used this is what "ate the disk." This is **manageable, not a reason to drop TM**:
- `tmutil thinlocalsnapshots / <bytes> <urgency>` reclaims on demand; macOS auto-thins under disk pressure.
- The cleaner lever for a removable destination: keep TM but expect local snapshots to accumulate while the drive is detached. Mitigations below.
- restic/borg/kopia can themselves *mount* an APFS snapshot to get a consistent read (advanced); not required for this user's data.

### 3. Sealed System Volume → bare-metal restore is Time-Machine-only on Apple Silicon
The System volume is a cryptographically **Signed System Volume (SSV)** sealed by Apple; the Mac boots from an immutable snapshot of it. Consequences (**verified, 0.95 confidence**):
- **No third-party tool makes a bootable clone anymore.** Bombich (CCC) themselves **deprecated bootable backups** and recommend "Standard Backup." SuperDuper bootable clones broke under Sequoia 15.2 and have been on-and-off since.
- A true full-system restore = **reinstall macOS (Recovery) + Migration Assistant from a Time Machine backup**. Everything else (restic, CCC standard, kopia) is **data-only**.
- For this user this is **fine**: OS reinstalls in ~30 min, code/media/docs are in git/gdrive/iCloud, and TM gives the smoothest Migration-Assistant path if he keeps it. **Bare-metal is a "plus," and only TM delivers it — another reason to keep TM rather than replace it.**

### 4. FileVault — turn it on, then everything-at-rest is covered for free
- **Enable FileVault** on the internal SSD (full-volume encryption at rest; M3 hardware AES, no perf cost). This protects the *source* — including keys, PHI, Signal — if the laptop is lost/stolen.
- **Encrypt the Time Machine destination:** TM offers "Encrypt Backups" (APFS encrypted) — **turn it on** so the 2 TB external is encrypted at rest too. Without this, your PHI sits in cleartext on a removable drive.
- **restic encrypts client-side** (AES-256) regardless of backend, so the B2 offsite copy is encrypted before it leaves the Mac — independent of FileVault. This is why restic (not Backblaze Personal) is the right offsite tier for PHI: *you* hold the key.

---

## Tool comparison (2026-verified)

| Tool / target | 3-2-1 role | Versioned | Encryption (who holds key) | macOS bare-metal | TCC/FDA burden | Maintenance | Cost (this user) | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Time Machine → 2 TB external** | local copy #2 | ✅ hourly/daily/weekly | ✅ APFS-encrypted dest (**you**) | ✅ **only true full restore** | **None** (exempt) | Very low | $0 (own drive) | **KEEP — versioning + bare-metal** |
| **restic → Backblaze B2 (S3 API)** | **offsite copy #3** | ✅ snapshots + `forget`/prune | ✅ client-side AES-256 (**you**) | ❌ data-only | FDA-on-shell once | Low (set-and-forget) | **~$2–4/mo** | **ADOPT — offsite/PHI tier** |
| restic → external | (alt local) | ✅ | ✅ (you) | ❌ | FDA-on-shell | Low | $0 | redundant with TM locally |
| borg / borgmatic | offsite | ✅ best dedup ratio | ✅ (you) | ❌ | FDA-on-shell + Python-process FDA mess | Medium | ~same as B2 | **Borg 2.0 still BETA (2.0.0b21, Mar 2026)**; stable 1.4.x lacks native cloud. Skip for "low-maint." |
| Kopia | offsite/local | ✅ | ✅ (you) AES-256-GCM | ❌ | FDA-on-shell | Low–Med | ~same as B2 | Strong (web UI, fast). Viable restic alternative; restic wins on community/tooling for a CLI user |
| Arq 7 | offsite (GUI) | ✅ | ✅ (you) | ❌ data-only | GUI app gets FDA easily | Very low | **$49.99 yr1, then $25/yr** + storage | Best if he wanted GUI; redundant given CLI comfort + restic |
| **Backblaze Personal (unlimited)** | offsite (GUI) | ⚠️ 30 d (1 yr free; Forever = paid) | ⚠️ vendor-managed by default; *optional* private key | ❌ | GUI app | Very low | **$99/yr flat, unlimited** | Cheapest "dumb unlimited," **but** weaker key control & version retention → **not** ideal for PHI |
| Carbon Copy Cloner | local clone | ⚠️ snapshots, not deep versions | dest encryption | ❌ (bootable deprecated) | App gets FDA | Low | $49.99 | Overlaps TM; no advantage here |
| SuperDuper | local clone | ❌ | dest encryption | ❌ (bootable broke in 15.2) | App gets FDA | Low | $27.95 | Skip |
| Storj | offsite (S3-compat) | ✅ via restic | ✅ (you, via restic) | ❌ | FDA-on-shell | Low | storage ~similar; **egress $10–20/TB**, only 1× free | Fine as B2 alternative; B2's 3× free egress + ecosystem win |
| rclone-crypt → cloud | offsite | ❌ **sync, not versioned** | ✅ (you) | ❌ | FDA-on-shell | Low | depends on backend | **Not a backup** — it mirrors deletions/corruption. Use as restic *backend transport* only |
| **iCloud (D&D + Photos)** | — | ⚠️ partial/30 d trash | vendor-managed | ❌ | n/a | n/a | (existing) | **NOT a backup** — it's *sync*: ransomware/accidental delete propagates. Counts as convenience, not a 3-2-1 copy |

---

## Why restic → B2 over the alternatives (decision rationale)

1. **vs. Backblaze Personal ($99/yr unlimited):** Personal is cheaper-per-GB at scale and zero-effort, but (a) default encryption is **vendor-managed** (private-key option exists but weakens their restore UX and you must never lose it), and (b) version history is **30 days** (1 yr free, "Forever" is a paid upsell with undisclosed pricing). For **PHI + keys**, you want client-held keys and long retention. restic gives both. At ~370 GB the cost gap is small (see costs).
2. **vs. Borg:** Borg 2.0 (native rclone/cloud) is **still beta** (2.0.0b21, 2026-03-16); stable Borg 1.4.x needs rclone/sshfs gymnastics to reach cloud. For "low maintenance + reliable," a beta backup tool holding your only offsite PHI copy is the wrong bet. restic has had first-class S3/B2 for years.
3. **vs. Kopia:** genuinely close — Kopia is faster and has a web UI. But for a **CLI-native** user who wants set-and-forget, restic's larger ecosystem (resticprofile, autorestic, every tutorial) and battle-tested S3 backend edge it out. *If he prefers a UI, Kopia is the no-regret swap — same architecture, same key-held-by-you property.*
4. **vs. Storj:** comparable storage price, but B2 gives **3× free egress** vs Storj's 1× and a deeper Mac/restic ecosystem. B2 also has documented restic quickstarts. Storj's decentralized model adds nothing for a single-user laptop.
5. **vs. rclone-crypt:** rclone is **sync**, not versioned backup — a corrupted/encrypted-by-malware file overwrites the good copy. Only use rclone as a *transport* under restic/borg, never as the backup itself.

---

## Concrete setup for THIS user

### Tier 1 — Time Machine → 2 TB external (local, versioned, bare-metal)
- **Keep it.** Enable **"Encrypt Backups"** when selecting the PNY SSD as TM destination (APFS-encrypted).
- Because the drive is **removable**, accept that TM falls back to local APFS snapshots while detached. Tame the disk-eating:
  - Plug in on a cadence (e.g., when at desk). TM auto-thins local snapshots once it backs up to the real destination.
  - If the SSD bites: `sudo tmutil thinlocalsnapshots / 20000000000 4` to reclaim ~20 GB on demand.
  - Optional: exclude bulky re-downloadable dirs from TM (`~/Library/Caches`, model caches, `node_modules`, the 47 GB already-in-gdrive media) via TM Options to shrink snapshot pressure.
- **This tier alone gives:** local copy + versioning + the only Apple-Silicon bare-metal restore path. **No TCC setup needed** (TM is exempt).

### Tier 2 — restic → Backblaze B2 (offsite, encrypted, PHI-safe)
**One-time:**
1. `brew install restic` (Apple-Silicon native, latest 0.18.x).
2. B2: create account → bucket (private) → **S3-compatible application key** (Backblaze's own restic docs recommend the S3 endpoint over the native B2 backend).
3. Store secrets in **macOS Keychain**, not in the plist or a dotfile:
   ```bash
   security add-generic-password -a "$USER" -s restic-b2-keyid   -w "<keyID>"
   security add-generic-password -a "$USER" -s restic-b2-key      -w "<applicationKey>"
   security add-generic-password -a "$USER" -s restic-repo-pass   -w "<long-random-restic-password>"
   ```
   The backup script pulls them via `security find-generic-password -s <name> -w`.
4. `restic init` against the bucket (this sets the **client-side encryption key** = the `restic-repo-pass`; **back this password up out-of-band** — losing it = losing the backup. Put it in your password manager AND a sealed offline copy).
5. **What to include:** `~` minus re-downloadable junk. Explicitly INCLUDE the high-value, must-encrypt set: `~/.ssh`, `~/.gnupg`, `~/.aws`, API-token configs, **WGS data + medical DuckDB paths**, **Signal** (`~/Library/Application Support/Signal`), and `~/Library` app data you care about. EXCLUDE caches, `node_modules`, model weights, and the 47 GB already in Google Drive (don't pay to store it twice).
6. **Solve TCC:** System Settings → Privacy & Security → **Full Disk Access** → add **`/bin/bash`** (or `/bin/zsh` if your script's shebang is zsh). *(Reveal hidden files with ⌘⇧. in the file picker, or drag the binary in.)* Without this, the launchd run silently skips Signal and `~/Library`.

**Schedule (survives the TCC wall):**
- A `launchd` LaunchAgent (`~/Library/LaunchAgents/local.restic.backup.plist`) running e.g. daily, invoking your shell script. Because launchd → bash (FDA-granted) → restic, protected files are readable.
- Script does: `restic backup <includes> --exclude-file=...` then `restic forget --prune` with a retention policy, e.g. `--keep-daily 7 --keep-weekly 4 --keep-monthly 12 --keep-yearly 3`.
- Add `restic check --read-data-subset=5%` weekly (cheap integrity probe) and a `restic check` monthly. Pipe failures to a notifier (e.g. write to a log the existing system-config tooling watches, or a simple `osascript` notification).
- **Low-maintenance bonus:** wrap with **`resticprofile`** (YAML config + schedule generation) or **`autorestic`** if you want to skip hand-writing the plist; both are CLI-native and well-suited to this user.

### Tier 3 (already done) — offsite app sync
- git/GitHub (code), Google Drive (47 GB media), iCloud (D&D) **stay as-is** but are explicitly **not counted** as backup copies for the sensitive set — they're sync, and restic→B2 is the real offsite copy. Keep the bash system-config-capture script; it accelerates the OS-reinstall step of a bare-metal recovery.

---

## Rough monthly cost

restic stores **deduplicated + compressed** data. The sensitive+personal set (excluding the 47 GB already in gdrive and excluding caches) is likely **~150–300 GB** of the 370 GB used — call it **300 GB worst-case** after dedup.

- **B2 storage:** $6/TB/mo → **300 GB ≈ $1.80/mo**; even a full 370 GB ≈ **$2.22/mo**.
- **B2 egress:** $0 in normal operation (you only download on restore; 3× free egress allowance dwarfs any restore).
- **Restore cost (rare):** downloading 300 GB is within 3× free allowance (900 GB) → **$0**.
- **Total ongoing: ~$2–4/month**, no per-API-call cost at this scale (Class A/B/C free; first 2,500 Class C/day free).
- Time Machine + FileVault + iCloud/gdrive/GitHub: **$0 incremental** (own drive / existing subscriptions).

**Compare:** Backblaze Personal flat $99/yr (~$8.25/mo) unlimited — *more* expensive than restic→B2 at this data size, with worse key control and shorter version history. The unlimited model only wins above ~1.5 TB of backed-up data, which this user isn't near.

---

## What I could NOT fully verify / caveats

- **"Forever" version history price (Backblaze Personal):** not publicly disclosed — quote-only. (Doesn't affect the recommendation; we're not using Personal.)
- **Time Machine FDA-exemption *mechanism*:** the operational fact (TM needs no FDA setup; third-party tools do) is solid and multiply-sourced. The *reason* ("private entitlement" vs. "Apple-signed system daemon under MAC") is contested — `verify_claim` pushed back on the "private entitlement" phrasing. I've stated only the operational fact in the recommendation and flagged the mechanism as uncertain. **No impact on the decision.**
- **Exact post-dedup backup size** is an estimate (150–300 GB). First `restic backup` will report the true number; cost scales linearly at $6/TB so even 2× off is ~$2/mo swing.
- **restic latest version:** confirmed 0.18.x line on Homebrew/Apple-Silicon; I did not pin the exact patch released in May 2026 (irrelevant — `brew` tracks it).
- **macOS version naming** ("Sequoia/Tahoe era 2026"): behavior described (SSV, TCC, bootable-clone deprecation) is stable across Sonoma→Sequoia→current; Bombich/SuperDuper bootable breakage was specifically Sequoia 15.2 (Dec 2024).

---

## Source Grades

| Claim | Source(s) | Grade | Notes |
|---|---|---|---|
| Backblaze Personal $99/yr, unlimited, no workstation limit, 30 d (1 yr free) version history | backblaze.com/cloud-backup/pricing + help docs (WebFetch + search) | **A** (vendor primary) | Forever-history price undisclosed |
| B2 $6/TB/mo, 3× free egress, $10/TB overage, Class A/B/C free | backblaze.com/cloud-storage/pricing + leanopstech 2026 | **A** (vendor primary) | cross-checked vendor + 3rd-party |
| Storj $20/TB egress (global), 1× free egress, Nov-2025 pricing change | storj.dev/dcs/pricing + forum | **A–** (vendor primary) | legacy-pricing grandfather through Oct 2026 |
| Arq 7 standalone $49.99 yr1 then $25/yr; Premium $59.99/yr w/ 1 TB | arqbackup.com pricing FAQ | **A** (vendor primary) | |
| restic 0.18.x, S3/B2 backend, Apple-Silicon | github.com/restic + restic.net + Backblaze docs | **A** | |
| Kopia AES-256-GCM, web UI, brew install, dedup | kopia.io + GitHub | **A** | |
| Borg 2.0 still beta (2.0.0b21, 2026-03-16); 1.4.4 stable (2026-03-19); rclone in 2.0 | borgbackup.org/releases + GitHub | **A** | beta status is the load-bearing fact |
| TCC blocks unattended backups; **grant FDA to `/bin/bash`, not the restic binary**, for script-driven launchd jobs | kith.org launchctl+FDA writeup + szymonkrajewski.pl + restic forum + lab.oceanview.ie (borgmatic) | **B+** (independent practitioners, convergent) | 3+ independent sources agree; not vendor-documented |
| Keychain via `security find-generic-password` for restic secrets | restic forum + practitioner blogs | **B+** | standard pattern |
| Sealed System Volume → only TM bare-metal; CCC/SuperDuper bootable deprecated/broken | verify_claim 0.95 + Bombich KB + eclecticlight.co + appleinsider (Sequoia 15.2) | **A** | strong multi-source convergence |
| Time Machine needs no FDA setup (operationally exempt) | eclecticlight.co TCC explainer + Apple docs | **A** (fact) / **C** (mechanism) | verify_claim contradicted the *"private entitlement"* mechanism — fact stands, mechanism flagged uncertain |
| FileVault hardware AES on Apple Silicon, no perf cost; TM "Encrypt Backups" | Apple support + general | **A** | |
| iCloud / rclone are sync not backup (propagate deletes/corruption) | general backup principle + rclone docs | **A** (principle) | |
| APFS local snapshots kept ~24h; `tmutil thinlocalsnapshots` | Apple/`tmutil` man + eclecticlight.co | **A** | |

*Grading: A = vendor primary or strong multi-source convergence · B+ = multiple independent practitioners agree, not vendor-documented · C = contested/single-source.*

---

## Deferred — query-in-place + sharing tier (R2 + Parquet) · TODO 2026-05-30

Decision driver is **egress, not storage price**: pulling 1 TB *out* of S3/GCS costs ~$90–123 **per download** (AWS ~$0.09/GB, GCS ~$0.12/GB — vendor-published, solid), and Glacier/Archive is a vault (hours to retrieve). So never cold-store a *working* dataset and re-download it.

Plan when ready:
- **Query-in-place:** datasets as **Parquet on Cloudflare R2** (R2's headline = **$0 egress**; storage ~$10–15/TB/mo — *re-verify at setup*). Query with **DuckDB httpfs**: `INSTALL httpfs; SET s3_endpoint='<acct>.r2.cloudflarestorage.com'; SELECT … FROM 'r2://bucket/x.parquet'` — Parquet pushdown reads only the scanned columns/rows. True "ping it online" without dragging the TB down.
- **Share (e.g. intel 1 TB → friends):** R2 public bucket / signed URLs → friends download free. NEVER S3/GCS (each friend-pull bills *you* ~$90–120 egress). Workspace Drive = no-code alt if seat storage headroom (Business Standard 2 TB / Plus 5 TB pooled, no per-GB egress).
- **Keep local / Modal:** working sets you compute on locally stay on the 2 TB; heavy compute → Modal (compute-to-data); genome CRAMs → cold/Modal (not query-in-place). Public re-downloadable data (FEC/CDC/UMLS/hg38) → URL manifest, store nothing.

First candidates to convert: the tabular corpus datasets + intel's shareable sets. (Storage $/TB figures above were pulled with a search tool flagged low-reliability for non-biomedical facts — treat as ballpark; the egress economics, which drive the decision, are solid vendor numbers.)
