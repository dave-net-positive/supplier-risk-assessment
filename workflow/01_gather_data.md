# Step 1–3: Data Gathering

## Step 1: Identify the Supplier Domain

1. Extract supplier name from trigger phrase.
2. Infer primary domain (e.g. "Codec Solutions" → "codec.co.uk").
3. Call `upguard-cyberrisk:get_vendor_details` with the inferred root domain.
   - Always use the **root domain**, not a subdomain.
   - If not found, try one or two plausible variants.
4. If still not found, ask: "I could not find [Supplier] in UpGuard. Do you know their primary domain?"
5. If user-provided domain still returns nothing: "UpGuard has no data for [domain]. Please add this
   vendor to your UpGuard watchlist and re-run once scanning has completed." Stop here.

---

## Step 2: Gather UpGuard Data

Call the following in parallel. Paginate `get_vendor_risks` if a `page_token` is returned.

| Tool | Data |
|---|---|
| `get_vendor_details(hostname)` | Overall score, industry comparison |
| `get_vendor_risks(hostname)` | Full risk list with severity and category |
| `get_vendor_vulnerabilities(hostname)` | CVE-level findings with CVSS |
| `list_vendor_questionnaires(hostname)` | Questionnaire status |

---

## Step 3: Gather M365 Context and Metadata Fields

Run these M365 searches in parallel:

```
outlook_email_search("supplier name")
outlook_email_search("domain")
chat_message_search("supplier name")
sharepoint_search("supplier name risk assessment")
sharepoint_search("supplier name questionnaire")
sharepoint_search("supplier name contract")
```

Also check conversation history and any uploaded documents.

**Collect the following metadata fields.** Record "Unknown — to be confirmed" where no reliable
source exists. Do not invent values.

| Field | Source and options |
|---|---|
| **Service** | What the supplier provides. Pull from conversation, email, SharePoint. Ask if unclear. |
| **Contractual status** | Check SharePoint/email. Options: Pre-contract / Active (expiry: [date]) / Renewal pending / No contract / Unknown |
| **Risk Assessment Owner** | InfoSec lead for this assessment. Default to role "Information Security" if no individual named. |
| **Final Submission date** | Deadline for the assessment. From email/conversation. Use "Not specified" if absent. |
| **Data Classification** | the organisation data categories this supplier handles. Infer from service/DPIA context. Options (list all that apply): Participant data / Genomic data / Health data / Staff data / Research data / Commercial data / None. Flag as question for internal owner if genuinely unclear. |
| **Access Management** | Systems/environments accessed; access type (read/write/admin); authentication method (SSO/MFA/VPN/password); whether access is periodically reviewed; whether a formal access request was followed. Note "Unknown" for any unknown element; flag unknown access as a governance gap. |
| **Fourth Parties** | Known sub-processors or significant technology dependencies. Check questionnaire responses and supplier docs. Flag unknown as question to supplier. |
| **SBOM** | Has a Software Bill of Materials been requested or received? Options: Provided / Requested (awaiting) / Not yet requested / Not applicable |
| **Ongoing Assurance** | Default by tier unless user specifies: Tier 1 = annual re-assessment + continuous UpGuard; Tier 2 = biennial + UpGuard; Tier 3/4 = UpGuard only + review on renewal. Note breach/material-change/ownership-change as standing out-of-cycle triggers. |
| **Notes** | Verbatim from assessor. Leave blank if nothing stated. Do not generate filler. |

When collection is complete, proceed to `workflow/02_assess_classify.md`.
