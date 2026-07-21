#!/usr/bin/env python3
"""
analyse_subdomains.py — Subdomain commonality and prevalence analysis.

Given a findings JSON file and a list of all observed subdomains, classifies
each finding's prevalence across tenant subdomains.

Usage:
    python3 analyse_subdomains.py \
        --findings findings.json \
        --subdomains subdomains.txt \
        --root-domain examplesupplier.com \
        [--org-subdomain org.examplesupplier.com] \
        --output findings_with_prevalence.json
    python3 analyse_subdomains.py --help

subdomains.txt: one subdomain per line (copy from UpGuard or browser inspection).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

PREVALENCE_THRESHOLDS = {
    # (min_fraction, label)
    "platform":  0.80,   # 80%+ of tenants → platform default
    "common":    0.50,   # 50-79% → common config
    "minority":  0.01,   # 1-49% → non-standard / minority
    "outlier":   0.00,   # ≤1 tenant → outlier (handled separately)
}

MIN_SAMPLE_SIZE = 5  # below this, skip prevalence analysis

def is_tenant_subdomain(sub, root_domain):
    """
    Heuristic: decide if a subdomain looks like a per-customer tenant.
    Tenant indicators: named prefix (clientname.sup.com), sequential numeric,
    or words like 'client', 'tenant', 'customer', 'instance' in the prefix.
    System subdomains like www, api, mail, demo, staging are excluded.
    """
    root = root_domain.lower().lstrip(".")
    sub  = sub.lower().strip()
    if not sub.endswith(f".{root}") and sub != root:
        return False
    prefix = sub[: -len(root) - 1] if sub.endswith(f".{root}") else ""
    if not prefix:
        return False
    system_prefixes = {
        "www", "api", "mail", "smtp", "imap", "ftp", "vpn", "cdn",
        "static", "assets", "media", "dev", "staging", "test", "uat",
        "demo", "sandbox", "preview", "beta", "alpha", "admin", "portal",
        "dashboard", "app", "web", "secure", "login", "auth", "sso",
        "support", "help", "docs", "status",
    }
    parts = prefix.split(".")
    base  = parts[0]
    if base in system_prefixes:
        return False
    return True

def classify_prevalence(finding_domains, tenant_subdomains, org_subdomain, root_domain):
    """
    Return (prevalence_label, confirmed_on_org_tenant, note).
    """
    n_tenants = len(tenant_subdomains)

    # Check if the organisation tenant is in finding's affected domains
    confirmed_org = False
    if org_subdomain:
        for fd in finding_domains:
            pattern = fd.replace("*", ".*")
            if re.match(pattern + "$", org_subdomain, re.IGNORECASE):
                confirmed_org = True
                break

    if n_tenants < MIN_SAMPLE_SIZE:
        return "unknown", confirmed_org, (
            f"Sample too small ({n_tenants} visible tenant subdomains) "
            "to draw conclusions about platform defaults."
        )

    # Count how many tenant subdomains match this finding's affected domains
    matching = set()
    for fd in finding_domains:
        pattern = "^" + re.escape(fd).replace(r"\*", ".*") + "$"
        for ts in tenant_subdomains:
            if re.match(pattern, ts, re.IGNORECASE):
                matching.add(ts)

    n_match  = len(matching)
    fraction = n_match / n_tenants

    if n_match <= 1:
        label = "outlier"
        note  = (
            f"Observed on {n_match} of approximately {n_tenants} visible tenant subdomains. "
            "This appears to be an isolated or legacy configuration rather than the supplier's "
            "standard platform. Included for confirmation rather than as a platform finding."
        )
    elif fraction >= PREVALENCE_THRESHOLDS["platform"]:
        label = "platform"
        note  = (
            f"Observed on {n_match} of approximately {n_tenants} visible tenant subdomains "
            f"({fraction:.0%}). This appears to reflect the supplier's standard deployment "
            "configuration."
        )
    elif fraction >= PREVALENCE_THRESHOLDS["common"]:
        label = "common"
        note  = (
            f"Observed on {n_match} of approximately {n_tenants} visible tenant subdomains "
            f"({fraction:.0%}). This is a common but not universal configuration."
        )
    else:
        label = "minority"
        note  = (
            f"Observed on {n_match} of approximately {n_tenants} visible tenant subdomains "
            f"({fraction:.0%}). This may be a non-standard or older deployment configuration."
        )

    return label, confirmed_org, note

def main():
    ap = argparse.ArgumentParser(
        description="Classify findings by subdomain prevalence across tenant infrastructure.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
subdomains.txt format: one subdomain per line.
  client1.example.com
  acme.example.com
  nhs.example.com
  ...

Findings whose affects[] patterns match a tenant subdomain are counted.
System subdomains (www, api, mail, etc.) are excluded from tenant count automatically.

Example:
  python3 analyse_subdomains.py \\
    --findings findings.json \\
    --subdomains all_subdomains.txt \\
    --root-domain examplesupplier.com \\
    --org-subdomain the organisation.examplesupplier.com \\
    --output findings_with_prevalence.json
""")
    ap.add_argument("--findings",      required=True, help="Findings JSON (from triage_risks.py)")
    ap.add_argument("--subdomains",    required=True, help="Text file of all observed subdomains, one per line")
    ap.add_argument("--root-domain",   required=True, help="Supplier root domain, e.g. examplesupplier.com")
    ap.add_argument("--org-subdomain", default="",    help="the organisation-specific subdomain if known, e.g. org.examplesupplier.com")
    ap.add_argument("--output",        required=True, help="Output findings JSON with prevalence added")
    args = ap.parse_args()

    findings    = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    all_subs    = [s.strip().lower() for s in Path(args.subdomains).read_text().splitlines() if s.strip()]
    tenant_subs = [s for s in all_subs if is_tenant_subdomain(s, args.root_domain)]

    print(f"Total subdomains: {len(all_subs)}")
    print(f"Tenant subdomains identified: {len(tenant_subs)}")

    if len(tenant_subs) < MIN_SAMPLE_SIZE:
        print(f"WARNING: Only {len(tenant_subs)} tenant subdomains visible. "
              "Prevalence analysis will return 'unknown' for all findings. "
              "Use standard confirmed/proxy framing.")

    for finding in findings:
        label, confirmed_org, note = classify_prevalence(
            finding.get("affects", []),
            tenant_subs,
            args.org_subdomain.lower(),
            args.root_domain,
        )
        finding["prevalence"]             = label
        finding["confirmed_on_org_tenant"] = confirmed_org
        finding["_prevalence_note"]       = note
        finding["_tenant_count"]          = len(tenant_subs)

    Path(args.output).write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    counts = defaultdict(int)
    for f in findings:
        counts[f["prevalence"]] += 1
    print("Prevalence summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"Output: {args.output}")

if __name__ == "__main__":
    main()
