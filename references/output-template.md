# Output Template — Structure Reference

Load this file only if you need to add a section not covered by `generate_report.py`.
All CSS, HTML structure, and boilerplate are embedded in the script. Do not reconstruct CSS
from this file; always use the script.

## Document structure (18 sections in order)

```
1.  Classification banner (colour-coded: RESTRICTED amber, INTERNAL blue, PUBLIC green, SECRET red)
2.  Document header (standalone-header — replaced by org-header if using org_html_page())
3.  Doc-meta card — ALL fields mandatory; use "Unknown — to be confirmed" if absent
4.  Changelog table — include from v1.1 onwards
5.  Introductory note — plain-English callout, two paragraphs
6.  DPIA callout (amber notice) — include when personal data in scope and no DPIA confirmed
7.  Scorecard tiles
8.  Access Management — before findings; sets context for why findings matter
9.  Findings table — Critical first; Severity / Finding / Plain-English / Status / Affects / Q
10. Accepted Risks sub-table — omit if none
11. Your options — decision framing, always present
12. Questions for the supplier — with Copy button
13. Questionnaire status
14. GDPR / Data Protection — always for Tier 1; elsewhere if PII identified
15. Fourth Parties and SBOM — always include; "Unknown" if not established
16. Recommended Actions table (P1 / P2 / P3)
17. Ongoing Assurance — tiles + trigger list
18. Notes — verbatim assessor text only; no generated filler
19. Methodology note — two-column grid
20. Standalone footer — AI disclaimer (replaced by org-footer if using org_html_page())
```

## Critical layout rules (do not deviate)

- `.plain-english`: NO `max-width`; width set on `<th width="44%">` only
- `.tag`: `display: block` (NOT `inline-block`); one domain per line, stacked vertically
- `.affects`: NO `white-space: nowrap`
- Column widths: `%` on `<th>` only; never fixed pixels

## the organisation brand integration

Use `org_html_page()` from the org-brand skill to wrap the body in the branded shell:

```python
from html_styles import org_html_page
html = org_html_page(
    title="[Supplier] — Supplier Security Risk Assessment",
    subtitle="the organisation Third-Party Risk Management",
    body_html=body_html,
    logo="white", embed_logo=True, embed_silhouette=True,
    full_width=True,
    extra_css=REPORT_CSS,  # the CSS block from generate_report.py
)
```

When org-brand is unavailable, generate_report.py uses standalone header/footer automatically.

## Doc-meta fields (all required)

Prepared by / Date / Last reviewed / Supplier / Service / Domain / Contractual status /
Internal owner / Risk Assessment Owner / Final Submission date / Data Classification /
Tier / Classification / Version
