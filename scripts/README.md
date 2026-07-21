# Scripts — the organisation Supplier Risk Assessment

These scripts are run via Claude's `bash_tool`. They are never loaded into context.
Claude copies the relevant script to `/home/claude/`, provides JSON input, runs it, and reads the output.

## Script summary

| Script | Input | Output | When |
|---|---|---|---|
| `triage_risks.py` | UpGuard risks JSON | findings.json (scored) | Step 5 |
| `analyse_subdomains.py` | findings.json + subdomains.txt | findings_with_prevalence.json | Step 5 |
| `generate_report.py` | assessment_data.json | [supplier]-risk-assessment.html | Step 8 |
| `update_report.py` | existing HTML + update_data.json | updated HTML | Step 10 |

## Typical workflow

```bash
# 1. Copy UpGuard risk data to file, then triage:
python3 triage_risks.py --input upguard_risks.json --tier 1 --output findings.json

# 2. If multiple tenant subdomains visible, analyse prevalence:
python3 analyse_subdomains.py \
  --findings findings.json \
  --subdomains all_subdomains.txt \
  --root-domain supplier.com \
  --org-subdomain org.supplier.com \
  --output findings.json   # overwrites in place

# 3. Claude reviews findings.json, writes/updates plain_english fields, assembles
#    full assessment_data.json, then generates report:
python3 generate_report.py --input assessment_data.json --output acme-risk.html

# 4. On review cycle, Claude assembles update_data.json, then:
python3 update_report.py --input acme-risk.html --update update_data.json --output acme-risk.html
```

## Important notes

- `triage_risks.py` generates **placeholder** plain_english text. Claude MUST review
  and replace these before calling `generate_report.py`.
- `update_report.py` relies on `data-id`, `data-finding-id`, and `data-question-id`
  attributes embedded by `generate_report.py`. Do not edit these attributes manually.
- Moving accepted risks to the Accepted Risks sub-table is handled by `update_report.py`:
  pass them in the `accepted` array and the script moves the row (creating the sub-table
  if the report had none) and adjusts the scorecard. The `notes` field and an explicit
  `scorecard_override` are applied the same way, so no manual HTML editing is needed.
- On a review cycle the script preserves the existing `plain_english` text for findings
  already in the report, so only genuinely new or changed findings need authored prose.
