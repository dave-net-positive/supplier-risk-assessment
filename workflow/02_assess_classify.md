# Step 4–6: Assessment and Classification

## Step 4: Determine Tier, Classification, and Domain Scope

**Tier** is based on CIA requirements of the operational service. Use judgement and available context.

| Tier | CIA Profile | Criteria |
|---|---|---|
| 1 (Critical) | High C/I/A | Processes the organisation personal/health/genomic data; critical system; Article 28 applies |
| 2 (Significant) | Medium C/I/A | Access to the organisation systems or non-personal data; meaningful dependency |
| 3 (Standard) | Low C/I/A | Low data access; commodity service; readily replaceable |
| 4 (Minimal) | Negligible | No the organisation data; no system access; informational relationship only |

**Classification** (default by tier unless user specifies otherwise):

| Tier | Default |
|---|---|
| 1 | RESTRICTED |
| 2/3 | INTERNAL |
| 4 | PUBLIC |

Scale: PUBLIC < INTERNAL < RESTRICTED < SECRET.
- Reducing below default: ask for justification; record it in the report.
- Increasing: no justification needed.

**Domain scope:** If the user specifies only certain subdomains are in use, filter findings
accordingly. Retain out-of-scope findings as informational, clearly marked.

---

## Step 5: Risk Triage and Subdomain Analysis

Load `references/risk-scoring.md` now for the the organisation scoring matrix.

### Run triage script

```bash
cp /mnt/skills/organization/supplier-risk-assessment/scripts/triage_risks.py /home/claude/
# Write UpGuard risk JSON to /home/claude/upguard_risks.json first, then:
python3 /home/claude/triage_risks.py \
  --input /home/claude/upguard_risks.json \
  --tier 1 \
  --output /home/claude/findings.json
```

The script outputs scored findings in the standard schema. Review the output and adjust any
finding where contextual factors warrant it (see risk-scoring.md for adjustment rules).

### Run subdomain analysis (if multiple tenant subdomains are visible)

```bash
cp /mnt/skills/organization/supplier-risk-assessment/scripts/analyse_subdomains.py /home/claude/
python3 /home/claude/analyse_subdomains.py \
  --findings /home/claude/findings.json \
  --output /home/claude/findings_with_prevalence.json
```

Prevalence classifications: **platform** (all/nearly all tenants) / **common** (>50%) /
**minority** (<50%) / **outlier** (one tenant only) / **unknown** (sample <5 tenants).

Framing rules:
- Platform default: attribute to the platform; treat as confirmed; ask as platform-level question.
- Outlier: frame with explicit uncertainty; use "Clarify scope" response type.
- If the organisation's own subdomain is known and shows the finding: treat as confirmed regardless of prevalence.
- Sample <5 tenants: skip prevalence analysis; use standard confirmed/proxy framing.

Do not list individual third-party customer subdomain names in the report.

---

## Step 6: Questionnaire Status and DPIA Check

**Questionnaire:**
- Completed: summarise key responses; flag gaps.
- In progress: note status and due date.
- Not sent: governance gap. Recommend MFQ (Tier 1) or GEN06_F (Tier 2/3). Note if dispatch
  is subject to TPRM programme review (owner: Caroline).

**DPIA check** — trigger if ANY of the following apply:
- Supplier is Tier 1
- Service description, email/Teams, or conversation references personal, health, genomic, employee, or participant data
- Supplier has access to the organisation systems where personal data is processed
- Reasonable inference from context (recruitment platform, HR system, CRM, finance system)

If personal data is in scope and no completed DPIA found:
1. Add a prominent amber callout in the report directing the user to run the DPIA skill.
2. Add a governance question card asking the supplier if they have their own DPIA available.

If unclear whether personal data is in scope: flag as a question for the internal owner.

Proceed to `workflow/03_generate_report.md`.
