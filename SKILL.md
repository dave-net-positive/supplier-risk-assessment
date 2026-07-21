---
name: supplier-risk-assessment
description: >
  Use this skill to produce a third-party supplier risk assessment for a named vendor. Triggers:
  "risk assessment for [supplier]", "let's do a risk assessment on [supplier]", "assess [supplier]",
  "security review of [supplier]", "TPRM for [supplier]", "can you check [supplier]". Trigger MUST
  include a supplier name. Also triggers when the user returns to an existing assessment with new
  information: questionnaire answers, risk waivers, domain scope changes, or re-scan data — use the
  Review and Update workflow (Step 9) in those cases. Orchestrates UpGuard CyberRisk MCP,
  Microsoft 365 email/Teams context, and conversation history to produce an audit-defensible HTML
  report. Always use this skill; do not improvise the workflow or output format.
---

# Supplier Risk Assessment — Skill Router

## How to use this skill

Load workflow files on demand as you reach each phase. Do not load all files upfront.
Scripts in `scripts/` are never read into context; copy them to `/home/claude/` and run
via `bash_tool`. The example report HTML is embedded inside `scripts/generate_report.py`
and does not need to be loaded separately.

## Workflow phases and files to load

| Phase | Steps | File to load |
|---|---|---|
| Data gathering | 1 (domain lookup), 2 (UpGuard), 3 (M365 + metadata) | `workflow/01_gather_data.md` |
| Assessment | 4 (tier/scope), 5 (risk triage), 6 (questionnaire/DPIA) | `workflow/02_assess_classify.md` |
| Report generation | 7 (questions), 8 (HTML), 9 (baseline) | `workflow/03_generate_report.md` |
| Review and update | 10 (diff, update, summary) | `workflow/04_review_update.md` |

Load `references/risk-scoring.md` only during Step 5 (risk triage).
Load `references/output-template.md` only if you need to add a section not covered by the scripts.

## Scripts (run via bash_tool, never read into context)

| Script | Purpose | When to use |
|---|---|---|
| `scripts/triage_risks.py` | Score and categorise UpGuard findings | Step 5 |
| `scripts/analyse_subdomains.py` | Subdomain commonality and prevalence analysis | Step 5 |
| `scripts/generate_report.py` | Generate complete HTML report from JSON | Step 8 |
| `scripts/update_report.py` | Apply surgical diff to existing report HTML | Step 10 |

## Running a script

```bash
# Copy from skill folder to working directory, then run
cp /mnt/skills/organization/supplier-risk-assessment/scripts/[script].py /home/claude/
python3 /home/claude/[script].py --help   # see input/output format
```

Each script reads a JSON input file and writes a JSON or HTML output file.
The script `--help` output describes the exact schema required.

## Edge cases (always apply, no file load needed)

- **Supplier not in UpGuard:** Ask for domain. If still not found, tell user to add to UpGuard watchlist and stop.
- **No M365 context:** Proceed with UpGuard data only; note in report.
- **Conflicting data:** Flag explicitly; do not resolve silently.
- **Critical finding waived without justification:** Apply waiver but add prominent note.
- **Classification downgrade without justification:** Ask once; if declined, apply with note.
- **Real PII encountered:** Stop. Warn user. Name the risk. Direct to Information Security Officer.
- **Context-only report (no UpGuard):** Label clearly as "Partial assessment: no scan data available."
