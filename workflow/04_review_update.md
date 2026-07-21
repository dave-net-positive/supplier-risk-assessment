# Step 10: Review and Update

Trigger this workflow when the user returns with any of:
- Answers to supplier questions (by Q number or topic)
- Confirmation of remediated findings
- Risk waivers or acceptances
- Domain scope changes
- New UpGuard scan data (re-scan or time passed)
- Uploaded documents (questionnaire response, pen test, DPA)

---

## Step 10a: Establish What Has Changed

1. Identify the existing report from context or ask the user to confirm which report to update.
2. Re-run UpGuard calls from Step 2 to get current data.
3. Fetch changes since baseline: `get_vendor_risk_diff(hostname, start_date=[baseline_date])`.
4. Categorise all changes:

| Change type | How to handle |
|---|---|
| Finding no longer detected | Mark resolved; note source (re-scan / supplier confirmation) |
| New finding detected | Add as new row; badge "New" |
| Supplier answered a question | Map to question ID; assess as satisfactory / partial / insufficient |
| Risk waived by user | Mark accepted; record rationale (or note if none given) |
| Domain scope changed | Refilter findings; update scope note |
| Uploaded document provides evidence | Extract key points; reference as source |

**Assessing supplier responses:**
- Satisfactory: directly addresses the finding with evidence or confirmed fix date.
- Partial: acknowledges the finding but response is incomplete or lacks commitment.
- Insufficient: vague, irrelevant, or does not address the technical reference.
- Conflicting: contradicts current scan data — flag the discrepancy; do not resolve silently.

---

## Step 10b: Produce the Updated Report

Assemble an update JSON file at `/home/claude/update_data.json`:

```json
{
  "report_path": "/home/claude/[supplier]-risk-assessment.html",
  "meta_updates": {
    "version": "1.1",
    "last_reviewed": "YYYY-MM-DD",
    "changelog_entry": {"version": "1.1", "date": "YYYY-MM-DD", "summary": ""}
  },
  "resolved": [
    {"id": "F001", "date": "YYYY-MM-DD", "source": "re-scan / supplier confirmation"}
  ],
  "new_findings": [
    {
      "id": "F007", "severity": "medium", "name": "", "technical_ref": "",
      "plain_english": "", "status": "new", "affects": [], "prevalence": "platform",
      "confirmed_on_org_tenant": false, "question_ref": "", "update_note": ""
    }
  ],
  "accepted": [
    {"id": "F003", "rationale": "", "accepted_by": "", "date": "YYYY-MM-DD"}
  ],
  "finding_updates": [
    {
      "id": "F002", "status": "partial",
      "update_note": "Supplier response 2026-01-15: [summary]. [Remaining concern.]"
    }
  ],
  "question_responses": [
    {
      "id": "Q1", "date": "YYYY-MM-DD",
      "summary": "", "status": "satisfactory"
    }
  ],
  "new_questions": [],
  "scope_change": null,
  "notes": null,
  "scorecard_override": null
}
```

Run the update script:

```bash
cp /mnt/skills/organization/supplier-risk-assessment/scripts/update_report.py /home/claude/
python3 /home/claude/update_report.py \
  --input /home/claude/[supplier]-risk-assessment.html \
  --update /home/claude/update_data.json \
  --output /home/claude/[supplier]-risk-assessment.html
```

The script applies changes in-place using `data-id` attributes embedded by the generator.
It does not regenerate the full report; only changed elements are touched.

**Accepted risks, notes, and the scorecard are handled by the script.** Put accepted
findings in the `accepted` array (the script moves the row, creating the Accepted Risks
table if needed, and adjusts the scorecard), set the `notes` field to update the notes box,
and use `scorecard_override` to record an explicit overall-risk decision.

**The one residual case** is a genuinely new section that the template and scripts do not
produce at all. Add it by extending `generate_report.py` with a new field so the scripts own
the section; that keeps the whole operation within the code path.

---

## Step 10c: Human-Readable Change Summary

After presenting the updated file, provide in chat:

- **Questions answered:** [n] — list each with satisfactory / partial / insufficient verdict
- **Resolved:** [n] findings confirmed remediated (list briefly)
- **New:** [n] new findings from re-scan (list briefly)
- **Accepted:** [n] risks waived (list with rationale or note if none given)
- **Unchanged:** [n] findings remain open with no response or action
- **Overall risk rating:** moved from [X] to [Y] / unchanged

Write for a non-technical reader. One or two sentences per bullet.

---

## Waiver and classification notes

**Critical finding waived without justification:** Apply waiver but add report note:
"This risk was accepted without documented justification. Rationale should be recorded
before this document is finalised."

**Classification reduced without justification:** Ask once. If declined, apply with note:
"Classification reduced from [default] at assessor's request. No justification recorded."
