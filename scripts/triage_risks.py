#!/usr/bin/env python3
"""
triage_risks.py — Convert UpGuard risk JSON to scored the organisation findings JSON.

Reads raw UpGuard get_vendor_risks output and applies the the organisation likelihood×impact
matrix, outputting findings in the standard assessment_data.json schema.

Usage:
    python3 triage_risks.py --input upguard_risks.json --tier 1 --output findings.json
    python3 triage_risks.py --help

Input: JSON list from UpGuard get_vendor_risks (the 'risks' array).
Output: JSON list of findings in standard schema, ready for assessment_data.json.
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# the organisation severity mapping from UpGuard
# ---------------------------------------------------------------------------
# UpGuard risk scores: 0-950. Higher = safer. Critical < 500, High 500-650, etc.
# UpGuard also provides a severity label. We map that to the organisation levels.

SEVERITY_MAP = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "info":     "low",
}

# Default likelihood and impact by the organisation severity
DEFAULT_SCORES = {
    "critical": {"likelihood": 4, "impact": 5},
    "high":     {"likelihood": 3, "impact": 4},
    "medium":   {"likelihood": 2, "impact": 3},
    "low":      {"likelihood": 1, "impact": 2},
}

# Tier 1 impact uplift: Tier 1 suppliers processing sensitive data get +1 impact
TIER_IMPACT_UPLIFT = {1: 1, 2: 0, 3: 0, 4: 0}

# UpGuard category to the organisation category
CATEGORY_MAP = {
    "web_application":    "Web Application Security",
    "network_security":   "Network and Infrastructure Security",
    "email_security":     "Email Security",
    "tls":                "TLS / Encryption",
    "dns_security":       "DNS Security",
    "patching":           "Patching and Vulnerability Management",
    "data_exposure":      "Data Exposure",
    "headers":            "Web Application Security",
    "cookies":            "Web Application Security",
    "csp":                "Web Application Security",
    "hsts":               "Web Application Security",
    "spf":                "Email Security",
    "dkim":               "Email Security",
    "dmarc":              "Email Security",
}

def ug_severity(risk):
    """Extract severity from UpGuard risk record."""
    sev = (risk.get("severity") or risk.get("risk_level") or "low").lower()
    return SEVERITY_MAP.get(sev, "low")

def ug_category(risk):
    """Map UpGuard category to the organisation category."""
    cat_raw = (risk.get("category") or risk.get("type") or "").lower().replace(" ", "_")
    for key, val in CATEGORY_MAP.items():
        if key in cat_raw:
            return val
    return "Network and Infrastructure Security"

def score_risk(severity, tier):
    """Calculate the organisation risk score with tier adjustment."""
    scores = DEFAULT_SCORES.get(severity, DEFAULT_SCORES["low"]).copy()
    uplift = TIER_IMPACT_UPLIFT.get(tier, 0)
    scores["impact"] = min(5, scores["impact"] + uplift)
    scores["risk_score"] = scores["likelihood"] * scores["impact"]
    return scores

def risk_level(score):
    if score >= 20: return "Critical"
    if score >= 12: return "High"
    if score >= 6:  return "Medium"
    return "Low"

def build_plain_english(risk):
    """Generate a placeholder plain-English explanation Claude should refine."""
    name = risk.get("name") or risk.get("title") or "Unknown finding"
    sev  = ug_severity(risk)
    desc = risk.get("description") or risk.get("detail") or ""
    return (
        f"[REVIEW REQUIRED] {name}. Severity: {sev.upper()}. "
        f"{'Detail: ' + desc[:200] if desc else 'No description available from scan.'} "
        f"Replace this with a plain-English explanation for the internal owner."
    )

def affected_domains(risk):
    """Extract affected domains/subdomains from a risk record."""
    domains = []
    for key in ("hosts", "affected_hosts", "domains", "subdomains", "host"):
        val = risk.get(key)
        if isinstance(val, list):
            domains.extend(str(v) for v in val)
        elif isinstance(val, str) and val:
            domains.append(val)
    return list(dict.fromkeys(domains)) or ["[domain unknown]"]

def triage(risks_input, tier):
    findings = []
    for i, risk in enumerate(risks_input, start=1):
        sev      = ug_severity(risk)
        scores   = score_risk(sev, tier)
        fid      = f"F{i:03d}"
        name     = risk.get("name") or risk.get("title") or f"Finding {i}"
        tech_ref = risk.get("cve") or risk.get("check_id") or risk.get("type") or name
        finding  = {
            "id":                    fid,
            "severity":              sev,
            "name":                  name,
            "technical_ref":         tech_ref,
            "plain_english":         build_plain_english(risk),
            "status":                "confirmed",
            "affects":               affected_domains(risk),
            "prevalence":            "unknown",       # set by analyse_subdomains.py
            "confirmed_on_org_tenant": False,         # set manually if known
            "question_ref":          "",              # set during question generation
            "update_note":           "",
            "_org_likelihood":       scores["likelihood"],
            "_org_impact":           scores["impact"],
            "_org_risk_score":       scores["risk_score"],
            "_org_risk_level":       risk_level(scores["risk_score"]),
            "_org_category":         ug_category(risk),
            "_upguard_raw":          {                # retain for reference; strip before final JSON
                "score":    risk.get("score"),
                "category": risk.get("category"),
                "cve":      risk.get("cve"),
            },
        }
        findings.append(finding)

    # Sort: critical first, then high, medium, low
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 4))
    return findings

def main():
    ap = argparse.ArgumentParser(
        description="Convert UpGuard risk JSON to the organisation scored findings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Input: The 'risks' array from UpGuard get_vendor_risks (save as JSON file).
Output: Findings array in standard assessment_data.json schema.

Fields marked _org_* are scoring metadata for your reference.
Fields marked _upguard_raw contain original UpGuard data for traceability.
Remove both prefixed groups before inserting into assessment_data.json,
or leave them — generate_report.py ignores unknown fields.

Plain-English explanations are generated as placeholders.
Claude MUST review and replace them with accurate, supplier-specific text
before calling generate_report.py.

Example:
  python3 triage_risks.py --input upguard_risks.json --tier 1 --output findings.json
""")
    ap.add_argument("--input",  required=True, help="JSON file containing UpGuard risks array")
    ap.add_argument("--tier",   required=True, type=int, choices=[1,2,3,4], help="Supplier tier (1-4)")
    ap.add_argument("--output", required=True, help="Output JSON file path")
    args = ap.parse_args()

    in_path  = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"ERROR: {in_path} not found", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    # Accept either a raw list or {"risks": [...]}
    risks = raw if isinstance(raw, list) else raw.get("risks", raw.get("data", []))

    findings = triage(risks, args.tier)
    out_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    print(f"Triaged {len(findings)} findings: " + ", ".join(f"{k}={v}" for k,v in sorted(counts.items())))
    print(f"Output: {out_path}")
    print("IMPORTANT: Review and replace all plain_english placeholder text before generating the report.")

if __name__ == "__main__":
    main()
