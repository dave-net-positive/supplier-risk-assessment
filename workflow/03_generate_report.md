# Step 7–9: Questions, Report Generation, and Baseline

## Step 7: Generate Supplier Questions

For every active finding and governance gap, produce one question card. Group closely related
findings (e.g. two missing headers) under a single question where sensible.

**Each question has three layers:**
1. Plain-English body — readable and forwardable by a non-technical liaison, no jargon.
2. Technical note — precise identifier (header name, CVE, cookie name, protocol).
3. Response type badge:
   - **Confirm and fix:** "Please confirm this will be addressed and provide an expected completion date."
   - **Explain and evidence:** "Please explain the control and provide supporting evidence."
   - **Clarify scope:** "Please confirm whether this applies to the organisation's systems, and if not, explain why."

**Tone:** Peer-to-peer, not auditor-to-auditee. "We noticed... could you confirm..." not "You failed to..."
Never mention UpGuard by name. Use "our security monitoring" or "our external scan."

**Standard governance questions to always include:**
- If no questionnaire sent: ask supplier to complete MFQ/GEN06_F (name it).
- If Article 28 DPA outstanding: ask supplier to confirm readiness.
- If DPIA in scope: ask if supplier has their own DPIA available.
- If fourth parties unknown: ask for sub-processor list and SBOM availability.

Number sequentially Q1, Q2... Add the question ref (e.g. "Q2") to the corresponding finding row.

---

## Step 8: Assemble JSON and Generate HTML Report

### 8a: Assemble assessment_data.json

Collect all gathered data into `/home/claude/assessment_data.json` using the schema below.
Every field must be present. Use `"Unknown — to be confirmed"` where data is unavailable.

```json
{
  "meta": {
    "supplier": "", "service": "", "domain": "",
    "contractual_status": "", "internal_owner": "",
    "risk_assessment_owner": "", "data_classification": "",
    "final_submission_date": "", "tier": "", "tier_num": 1,
    "classification": "RESTRICTED", "version": "1.0",
    "date": "YYYY-MM-DD", "last_reviewed": "YYYY-MM-DD",
    "changelog": [{"version": "1.0", "date": "YYYY-MM-DD", "summary": "Initial assessment"}]
  },
  "upguard_score": 0,
  "scorecard": {
    "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0,
    "accepted_count": 0, "questionnaire_status": "Not sent", "overall_risk": "High"
  },
  "dpia_required": false,
  "findings": [
    {
      "id": "F001", "severity": "high", "name": "", "technical_ref": "",
      "plain_english": "", "status": "confirmed",
      "affects": ["subdomain.*"], "prevalence": "platform",
      "confirmed_on_org_tenant": false, "question_ref": "Q1", "update_note": ""
    }
  ],
  "accepted_risks": [],
  "questions": [
    {
      "id": "Q1", "severity": "high", "title": "", "body": "",
      "technical_ref": "", "prevalence_note": "", "response_type": "confirm"
    }
  ],
  "access_management": {
    "items": [
      {"label": "Access type", "value": ""},
      {"label": "Systems / environments accessed", "value": ""},
      {"label": "Authentication method", "value": ""},
      {"label": "Access review", "value": ""},
      {"label": "Formal access request process", "value": ""},
      {"label": "Privileged / admin access", "value": ""}
    ],
    "gaps": []
  },
  "fourth_parties": [],
  "sbom_status": "not_requested",
  "sbom_note": "",
  "fourth_parties_note": "",
  "questionnaire_status_text": "",
  "gdpr_items": [],
  "recommended_actions": [],
  "ongoing_assurance": {
    "frequency": "Annual", "monitoring": "UpGuard (live)",
    "next_review": "", "responsible": "Information Security",
    "triggers": [
      "Material security breach at the supplier or any confirmed fourth party",
      "Significant change to the service, platform, or data processing scope",
      "Contract renewal or material amendment",
      "Change of ownership or organisational restructure at the supplier",
      "UpGuard score drops below 600 or a new Critical finding is detected",
      "Notification of an incident affecting the organisation data"
    ]
  },
  "notes": "",
  "methodology": {
    "how": "Automated scanning via security monitoring platform and direct inspection of publicly accessible systems on [date]. No information requested from or provided by the supplier.",
    "context": "Approximately [n] tenant subdomains were assessed. Individual third-party customer subdomain names are not disclosed. Findings marked 'Platform default' reflect the supplier's observed standard configuration."
  }
}
```

### 8b: Run the report generator

```bash
cp /mnt/skills/organization/supplier-risk-assessment/scripts/generate_report.py /home/claude/
python3 /home/claude/generate_report.py \
  --input /home/claude/assessment_data.json \
  --output /home/claude/[supplier-slug]-risk-assessment.html
```

Copy the output to `/mnt/user-data/outputs/` and present with `present_files`.

### 8c: Required output properties

- British English throughout; no em dashes.
- Classification banner colour-coded (RESTRICTED amber, INTERNAL blue, PUBLIC green, SECRET red).
- AI disclaimer footer on every page.
- All findings cite their source (UpGuard scan date, live inspection, email context).
- Plain-English explanation mandatory for every finding.
- "Your options" decision section always present.

### 8d: Verbal summary in chat

After presenting the file, provide a brief chat summary covering:
- UpGuard score and trend
- Top 3 findings by severity
- Questionnaire status
- Recommended next action

---

## Step 9: Record Assessment Baseline

Record the following in conversation context for use during review cycles:

- Report filename and output path
- Assessment date and UpGuard score
- Full list of finding IDs, names, severities, and statuses
- Full list of question IDs mapped to finding IDs
- Domain scope agreed at assessment
- Risks already accepted/waived at issue
