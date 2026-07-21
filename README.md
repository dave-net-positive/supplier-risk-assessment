# Supplier Risk Assessment

An Agent Skill for producing audit-defensible third-party supplier security risk
assessments. It turns vendor scan data plus contextual signals into a scored,
categorised risk triage and a self-contained HTML report.

## What it does

- **Triage and score** findings against a documented risk-scoring matrix
  (`references/risk-scoring.md`).
- **Subdomain commonality / prevalence analysis** (`scripts/analyse_subdomains.py`).
- **Generate a complete HTML report** from structured JSON
  (`scripts/generate_report.py`), and apply surgical diffs on re-scan
  (`scripts/update_report.py`).
- A phased workflow (gather to assess to report to review) under `workflow/`.

## How it's built

Authored as an Agent Skill: a thin router (`SKILL.md`) that loads workflow files
on demand, with the deterministic work (scoring, report rendering) done by Python
scripts rather than the model. Each script reads a JSON input and writes JSON or
HTML; run `python3 scripts/<name>.py --help` for the exact schema.

## Dependencies

The scripts are standalone Python. The end-to-end workflow assumes access to
vendor scan data (for example an UpGuard CyberRisk export) supplied as JSON; the
scripts do not call any external API themselves.

## Note

Generalised from internal GRC tooling. Provided as-is under the MIT licence;
adapt the scoring matrix and templates to your own risk appetite.
