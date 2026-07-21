# the organisation Risk Scoring Reference

## Supplier Tiers

Tier is determined by the CIA (Confidentiality, Integrity, Availability) requirements of the
operational service that requires this supplier. The assessor determines tier based on judgement
and available context. There is no central tier register; tier is set per assessment.

| Tier | CIA Profile | Criteria |
|---|---|---|
| Tier 1 (Critical) | High C, High I, or High A | Processes the organisation personal, health, or genomic data; critical business system; UK GDPR Article 28 applies; loss or compromise would materially affect the organisation operations or participants |
| Tier 2 (Significant) | Medium C/I/A | Has access to the organisation systems or non-personal data; meaningful business dependency; disruption would cause operational impact |
| Tier 3 (Standard) | Low C/I/A | Low data access; limited or no the organisation-owned data; commodity service; readily replaceable |
| Tier 4 (Minimal) | Negligible | No the organisation data; no system access; informational or arms-length relationship only |

---

## Document Classification

| Classification | Colour in report | Usage |
|---|---|---|
| PUBLIC | Green (#2d7a4f / #edf7f1) | Information intended for public release; no controls required |
| INTERNAL | Blue (#2c4a7c / #e8eef7) | General internal use; not for external distribution without authorisation |
| RESTRICTED | Amber (#c07000 / #fdf6e8) | Limited distribution; sensitive; Tier 1 (Critical) supplier default |
| SECRET | Red (#c0392b / #fdf0ee) | Highly sensitive; strictly controlled distribution |

**Default classification by tier:**

| Tier | Default |
|---|---|
| Tier 1 | RESTRICTED |
| Tier 2 | INTERNAL |
| Tier 3 | INTERNAL |
| Tier 4 | PUBLIC |

**Classification changes:**
- Reducing classification below the default requires justification from the assessor, recorded
  in the report.
- Increasing classification requires no justification.

---

## Risk Matrix

Risk Score = Likelihood x Impact

### Likelihood

| Score | Label | Description |
|---|---|---|
| 5 | Almost certain (>70%) | No current strategy will resolve this issue |
| 4 | Likely (45-70%) | Current strategy will probably not resolve this |
| 3 | Moderate (25-45%) | Current strategy may not resolve this |
| 2 | Unlikely (5-25%) | Current strategy should resolve this |
| 1 | Rare (<5%) | Very unlikely to occur |

### Impact

| Score | Label | Examples |
|---|---|---|
| 5 | Catastrophic | Significant data breach; regulatory sanction; loss of the organisation licence to operate |
| 4 | Major | Notifiable breach; significant operational disruption; formal regulatory scrutiny |
| 3 | Moderate | Limited breach; moderate disruption; manageable regulatory engagement |
| 2 | Minor | Small-scale incident; contained; low regulatory risk |
| 1 | Negligible | Trivial impact; easily remediated; no regulatory consequence |

### Risk Level

| Score | Level | Treatment |
|---|---|---|
| 20-25 | Critical | Immediate escalation; block procurement/deployment until resolved or accepted at director level |
| 12-19 | High | Formal remediation plan required; time-bound; owner assigned |
| 6-11 | Medium | Remediation planned; tracked on risk register |
| 1-5 | Low | Monitor; review at next assessment cycle |

---

## Mapping UpGuard Severity to the organisation Risk

| UpGuard Label | the organisation Risk Level | Default Likelihood | Default Impact |
|---|---|---|---|
| Critical | Critical | 4 | 5 |
| High | High | 3 | 4 |
| Medium | Medium | 2 | 3 |
| Low | Low | 1 | 2 |

**Contextual adjustments:**

- Tier 1 supplier processing health/genomic data: increase impact by 1.
- Finding confirmed on live production system by independent inspection: increase likelihood by 1.
- Supplier has acknowledged the finding and provided a documented remediation timeline: decrease
  likelihood by 1.
- Compensating control evidence available and verified: decrease impact by 1.
- Finding applies only to out-of-scope domains (as agreed with internal owner): do not include
  in active risk score; retain as informational.

---

## Risk Register Entry Format

| Field | Content |
|---|---|
| Risk ID | RR-[YYYY]-[NNN] |
| Date raised | ISO date |
| Supplier | Name and domain |
| Finding | Short description |
| Source | UpGuard scan / live inspection / questionnaire / email context |
| Category | See category list in SKILL.md |
| Likelihood | 1-5 |
| Impact | 1-5 |
| Risk Score | L x I |
| Risk Level | Critical / High / Medium / Low |
| Owner | Dave Sherwood (InfoSec) or assigned stakeholder |
| Status | Open / Accepted / Mitigated / Closed |
| Notes | Remediation action or acceptance rationale |

---

## GDPR and DPA 2018 Considerations

For Tier 1 suppliers (or any supplier identified as processing personal or special category data):

- **Article 28 UK GDPR:** A Data Processing Agreement or equivalent contractual schedule is
  mandatory before processing begins.
- **Article 46 UK GDPR:** If data is transferred outside the UK or EEA, an appropriate transfer
  mechanism is required (IDTA, SCCs, adequacy decision).
- **Section 62 DPA 2018 / Caldicott Principles:** Apply to health and genomic data specifically.
- **Article 35 UK GDPR:** A DPIA is required where processing is likely to result in high risk
  to data subjects.

Flag any gaps in contractual or governance coverage as separate risk items in the report.

---

## Versioning Convention

| Version | Meaning |
|---|---|
| 1.0 | Initial assessment |
| 1.x | Minor update (waiver, scope change, questionnaire response) |
| 2.0 | Full re-assessment following re-scan or material change in supplier posture |
