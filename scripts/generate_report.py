#!/usr/bin/env python3
"""
generate_report.py — the organisation Supplier Risk Assessment HTML Generator

Reads assessment_data.json and writes a fully branded HTML report.
Embeds all CSS and structure so Claude never needs to write HTML inline.

Usage:
    python3 generate_report.py --input assessment_data.json --output report.html
    python3 generate_report.py --help
"""

import argparse
import json
import sys
from pathlib import Path
from html import escape as esc
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def badge(severity):
    return f'<span class="badge badge-{severity}">{severity.upper()}</span>'

def status_badge(status):
    labels = {
        "confirmed": "Confirmed", "partial": "Partial fix", "resolved": "Resolved",
        "accepted": "Accepted", "new": "New", "conflict": "Conflict",
        "unsatisfactory": "Response unsatisfactory",
    }
    return f'<span class="status-badge status-{status}">{labels.get(status, status)}</span>'

def prev_badge(prevalence):
    labels = {
        "platform": "Platform default", "common": "Common config",
        "minority": "Non-standard", "outlier": "Outlier", "unknown": "Sample too small",
    }
    if prevalence not in labels:
        return ""
    return f'<span class="prev-badge prev-{prevalence}">{labels[prevalence]}</span>'

def classification_label(level):
    descs = {
        "PUBLIC": "PUBLIC — No distribution controls.",
        "INTERNAL": "INTERNAL — Not for external distribution without authorisation.",
        "RESTRICTED": "RESTRICTED — Limited distribution. Not for external disclosure without authorisation.",
        "SECRET": "SECRET — Strictly controlled distribution.",
    }
    return descs.get(level.upper(), level)

def score_colour(score):
    if score >= 750: return "score-green"
    if score >= 600: return "score-amber"
    return "score-red"

def sbom_class(status):
    return {
        "provided": "sbom-provided", "requested": "sbom-requested",
        "not_requested": "sbom-not-requested", "na": "sbom-na",
    }.get(status, "sbom-na")

def sbom_label(status):
    return {
        "provided": "Provided", "requested": "Requested — awaiting response",
        "not_requested": "Not yet requested", "na": "Not applicable",
    }.get(status, status)

def rt_class(rt):
    return {"confirm": "rt-confirm", "evidence": "rt-evidence", "scope": "rt-scope"}.get(rt, "rt-confirm")

def rt_label(rt):
    return {
        "confirm": "Confirm and fix",
        "evidence": "Explain and evidence",
        "scope": "Clarify scope",
    }.get(rt, rt)

def priority_class(p):
    return {"P1": "p1", "P2": "p2", "P3": "p3"}.get(p.upper(), "")

def tags_html(affects):
    return "".join(f'<span class="tag">{esc(d)}</span>' for d in affects)

def tier_label(num):
    return {1: "1 (Critical)", 2: "2 (Significant)", 3: "3 (Standard)", 4: "4 (Minimal)"}.get(num, str(num))

# ---------------------------------------------------------------------------
# CSS (canonical; copied verbatim from example-report.html)
# ---------------------------------------------------------------------------
CSS = """
:root {
  --org-blue:     #005f6f;
  --org-blue-20:  rgba(0, 95, 111, 0.2);
  --org-base:     #f4efde;
  --font:         'Libre Franklin', 'Tahoma', sans-serif;
  --ink:          #1a1a1a; --ink-light:  #5a5a5a; --ink-muted:  #8a8a8a;
  --paper:        #f9f7f4; --paper-dark: #f0ede8; --rule:       #ddd9d3;
  --critical:        #7b0000; --critical-bg: #fde8e8; --critical-border: #d4a0a0;
  --high:            #c0392b; --high-bg:     #fdf0ee; --high-border:     #e8c5c0;
  --medium:          #c07000; --medium-bg:   #fdf6e8; --medium-border:   #e8d9b0;
  --low:             #2d7a4f; --low-bg:      #edf7f1; --low-border:      #b8ddc8;
  --cls-public:     #2d7a4f; --cls-public-bg:     #edf7f1;
  --cls-internal:   #005f6f; --cls-internal-bg:   #e6f0f2;
  --cls-restricted: #c07000; --cls-restricted-bg: #fdf6e8;
  --cls-secret:     #7b0000; --cls-secret-bg:     #fde8e8;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--org-base); color: var(--ink); font-family: var(--font); font-size: 14px; line-height: 1.6; }
.report-page { max-width: 1060px; margin: 0 auto; background: white; }
.report-content { padding: 36px 40px 60px; }
.standalone-header { background: var(--org-blue); color: white; padding: 28px 40px; display: flex; justify-content: space-between; align-items: center; }
.standalone-header .org-name { font-size: 13px; font-weight: 600; letter-spacing: 0.05em; opacity: 0.85; text-transform: uppercase; }
.standalone-header .doc-type { font-size: 22px; font-weight: 700; margin-top: 4px; }
.standalone-footer { background: var(--org-blue); color: white; padding: 16px 40px; font-size: 12px; display: flex; justify-content: space-between; align-items: center; }
.standalone-footer .ai-note { opacity: 0.8; font-style: italic; }
.classification-banner { text-align: center; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; padding: 8px 0; margin-bottom: 24px; border-radius: 2px; }
.classification-public     { background: var(--cls-public-bg);     color: var(--cls-public);     border: 1px solid var(--low-border); }
.classification-internal   { background: var(--cls-internal-bg);   color: var(--cls-internal);   border: 1px solid #b8d4d9; }
.classification-restricted { background: var(--cls-restricted-bg); color: var(--cls-restricted); border: 1px solid var(--medium-border); }
.classification-secret     { background: var(--cls-secret-bg);     color: var(--cls-secret);     border: 1px solid var(--critical-border); }
.doc-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 32px; border-bottom: 2px solid var(--rule); padding-bottom: 24px; margin-bottom: 24px; }
.doc-header-title h1 { font-family: Georgia, serif; font-size: 22px; font-weight: 700; line-height: 1.3; color: var(--org-blue); margin-bottom: 4px; }
.doc-header-title h1 span { display: block; font-size: 13px; font-weight: 400; color: var(--ink-muted); margin-top: 4px; }
.doc-meta { font-size: 12.5px; line-height: 1.85; color: var(--ink-light); min-width: 280px; background: var(--paper-dark); border: 1px solid var(--rule); padding: 14px 18px; flex-shrink: 0; }
.doc-meta strong { color: var(--ink); display: inline-block; min-width: 145px; }
.doc-meta .meta-divider { border: none; border-top: 1px solid var(--rule); margin: 8px 0; }
.changelog { margin-bottom: 28px; }
.section-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--ink-muted); margin-bottom: 8px; }
.section-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.changelog-table { width: auto; font-size: 12px; border-collapse: collapse; }
.changelog-table th { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); background: var(--paper-dark); padding: 6px 20px 6px 10px; border-bottom: 2px solid var(--rule); text-align: left; }
.changelog-table td { padding: 6px 20px 6px 10px; border-bottom: 1px solid var(--rule); color: var(--ink-light); }
.intro { border-left: 4px solid var(--org-blue); background: var(--cls-internal-bg); padding: 16px 20px; margin-bottom: 28px; font-size: 13.5px; color: var(--ink-light); line-height: 1.65; }
.intro p { margin-bottom: 10px; } .intro p:last-child { margin-bottom: 0; } .intro strong { color: var(--ink); font-weight: 600; }
.notice { padding: 14px 18px; font-size: 13px; margin-bottom: 20px; border-radius: 2px; }
.notice-amber { background: var(--medium-bg); border: 1px solid var(--medium-border); }
.notice-amber strong { color: var(--medium); }
.scorecard { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 28px; }
.score-tile { flex: 1; min-width: 100px; background: white; border: 1px solid var(--rule); padding: 12px 14px; text-align: center; }
.tile-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-muted); margin-bottom: 5px; }
.tile-value { font-size: 24px; font-weight: 700; font-family: Georgia, serif; line-height: 1.1; }
.tile-sub { font-size: 11px; color: var(--ink-muted); margin-top: 3px; }
.score-green .tile-value { color: var(--low); } .score-amber .tile-value { color: var(--medium); } .score-red .tile-value { color: var(--critical); }
.tile-critical .tile-value { color: var(--critical); } .tile-high .tile-value { color: var(--high); } .tile-medium .tile-value { color: var(--medium); } .tile-low .tile-value { color: var(--low); }
.access-item { background: white; border: 1px solid var(--rule); padding: 12px 14px; }
.access-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-muted); margin-bottom: 4px; }
.access-value { font-size: 13px; color: var(--ink-light); line-height: 1.5; }
.access-value strong { color: var(--ink); font-weight: 600; }
.access-gap { background: var(--medium-bg); border-left: 3px solid var(--medium); padding: 10px 14px; font-size: 12.5px; color: var(--medium); margin-top: 10px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 8px; }
th { background: var(--org-blue); color: white; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; padding: 8px 12px; text-align: left; font-weight: 700; }
td { padding: 12px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }
tr:last-child td { border-bottom: none; } tr:hover td { background: rgba(0,95,111,0.04); }
.severity-critical { background: var(--critical-bg); } .severity-high { background: var(--high-bg); } .severity-medium { background: var(--medium-bg); } .severity-low { background: var(--low-bg); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap; }
.badge-critical { background: var(--critical); color: white; } .badge-high { background: var(--high); color: white; } .badge-medium { background: var(--medium); color: white; } .badge-low { background: var(--low); color: white; }
.badge-gov { background: var(--org-blue); color: white; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-weight: 700; text-transform: uppercase; white-space: nowrap; }
.status-badge { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-weight: 600; white-space: nowrap; }
.status-confirmed { background: var(--high-bg); color: var(--high); border: 1px solid var(--high-border); }
.status-partial   { background: var(--medium-bg); color: var(--medium); border: 1px solid var(--medium-border); }
.status-resolved  { background: var(--low-bg); color: var(--low); border: 1px solid var(--low-border); }
.status-accepted  { background: var(--medium-bg); color: var(--medium); border: 1px solid var(--medium-border); }
.status-new       { background: var(--medium-bg); color: var(--medium); border: 1px solid var(--medium-border); }
.status-conflict  { background: var(--critical-bg); color: var(--critical); border: 1px solid var(--critical-border); font-weight: 700; }
.status-unsatisfactory { background: var(--critical-bg); color: var(--critical); border: 1px solid var(--critical-border); }
.prev-badge { display: inline-block; padding: 2px 7px; border-radius: 2px; font-size: 10px; font-weight: 600; border: 1px solid; white-space: nowrap; margin-top: 3px; }
.prev-platform  { background: var(--high-bg);    color: var(--critical); border-color: var(--critical-border); }
.prev-common    { background: var(--medium-bg);  color: var(--medium);   border-color: var(--medium-border); }
.prev-minority  { background: var(--paper-dark); color: var(--ink-light); border-color: var(--rule); }
.prev-outlier   { background: var(--paper-dark); color: var(--ink-muted); border-color: var(--rule); font-style: italic; }
.prev-unknown   { background: var(--paper-dark); color: var(--ink-muted); border-color: var(--rule); }
.prev-confirmed-tenant { background: var(--low-bg); color: var(--low); border-color: var(--low-border); margin-left: 3px; }
.risk-name { font-weight: 600; color: var(--ink); margin-bottom: 3px; font-size: 13px; }
.risk-technical { font-family: 'Courier New', monospace; font-size: 10.5px; color: var(--ink-muted); margin-top: 1px; }
/* CRITICAL: plain-english NO max-width; width set on <th> only */
.plain-english { font-size: 13px; line-height: 1.6; color: var(--ink-light); }
.plain-english strong { color: var(--ink); font-weight: 500; }
/* CRITICAL: affects NO white-space:nowrap; tags display:block */
.tag { display: block; background: var(--paper-dark); border: 1px solid var(--rule); border-radius: 2px; padding: 2px 6px; font-size: 10px; font-family: 'Courier New', monospace; color: var(--ink-light); margin-bottom: 3px; width: fit-content; }
.update-note { font-size: 11px; color: var(--ink-muted); margin-top: 8px; padding: 5px 8px; background: var(--paper-dark); border-left: 2px solid var(--rule); line-height: 1.5; }
.update-note.conflict { color: var(--critical); border-left-color: var(--critical-border); background: var(--critical-bg); }
.row-resolved td { opacity: 0.55; } .row-resolved .risk-name, .row-resolved .plain-english { text-decoration: line-through; } .row-resolved .update-note { text-decoration: none; opacity: 1; }
.q-ref { font-size: 11px; color: var(--org-blue); font-weight: 700; white-space: nowrap; }
.options-box { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px; }
.option-card { border: 1px solid var(--rule); padding: 18px 20px; background: white; }
.option-card p { font-size: 13px; color: var(--ink-light); line-height: 1.6; }
.option-a h3 { color: var(--org-blue); border-bottom: 2px solid var(--org-blue); padding-bottom: 6px; margin-bottom: 10px; font-size: 14px; }
.option-b h3 { color: var(--ink-light); border-bottom: 2px solid var(--rule); padding-bottom: 6px; margin-bottom: 10px; font-size: 14px; }
.question-card { border: 1px solid var(--rule); border-left: 4px solid; background: white; padding: 16px 20px; margin-bottom: 12px; }
.question-card.severity-critical { border-left-color: var(--critical); } .question-card.severity-high { border-left-color: var(--high); }
.question-card.severity-medium { border-left-color: var(--medium); } .question-card.severity-low { border-left-color: var(--low); }
.question-card.severity-governance { border-left-color: var(--org-blue); }
.question-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.question-number { font-family: Georgia, serif; font-weight: 700; font-size: 15px; color: var(--org-blue); min-width: 28px; }
.question-title  { font-weight: 600; font-size: 13.5px; color: var(--ink); flex: 1; }
.question-body p { font-size: 13.5px; color: var(--ink-light); line-height: 1.65; margin-bottom: 6px; }
.question-technical { font-size: 11px; font-family: 'Courier New', monospace; color: var(--ink-muted); background: var(--paper-dark); border: 1px solid var(--rule); padding: 6px 10px; margin-top: 8px; }
.tech-label { font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); margin-right: 6px; }
.question-prevalence { font-size: 11px; color: var(--ink-muted); margin-top: 6px; margin-bottom: 2px; }
.question-prevalence strong { color: var(--ink-light); }
.question-response { margin-top: 10px; padding: 8px 12px; background: var(--paper-dark); border-left: 3px solid var(--rule); font-size: 12px; color: var(--ink-light); }
.response-label { font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); display: block; margin-bottom: 3px; }
.rt-badge { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-weight: 600; border: 1px solid; }
.rt-confirm  { background: var(--medium-bg); color: var(--medium); border-color: var(--medium-border); }
.rt-evidence { background: var(--cls-internal-bg); color: var(--cls-internal); border-color: #b8d4d9; }
.rt-scope    { background: var(--paper-dark); color: var(--ink-light); border-color: var(--rule); }
.gdpr-item { border-left: 3px solid #b8d4d9; padding: 10px 14px; background: white; margin-bottom: 10px; }
.gdpr-label  { font-weight: 600; font-size: 13px; color: var(--org-blue); margin-bottom: 2px; }
.gdpr-detail { font-size: 13px; color: var(--ink-light); line-height: 1.55; }
.sbom-status { display: inline-block; padding: 3px 10px; border-radius: 2px; font-size: 11px; font-weight: 600; border: 1px solid; }
.sbom-provided     { background: var(--low-bg);      color: var(--low);      border-color: var(--low-border); }
.sbom-requested    { background: var(--medium-bg);   color: var(--medium);   border-color: var(--medium-border); }
.sbom-not-requested { background: var(--high-bg);    color: var(--high);     border-color: var(--high-border); }
.sbom-na           { background: var(--paper-dark);  color: var(--ink-muted); border-color: var(--rule); }
.assurance-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.assurance-tile { background: white; border: 1px solid var(--rule); padding: 14px 16px; text-align: center; }
.assurance-tile .tile-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-muted); margin-bottom: 5px; }
.assurance-tile .tile-value { font-size: 15px; font-weight: 700; color: var(--org-blue); line-height: 1.3; }
.trigger-list { list-style: none; padding: 0; margin: 0; }
.trigger-list li { font-size: 13px; color: var(--ink-light); padding: 6px 0 6px 18px; border-bottom: 1px solid var(--rule); position: relative; }
.trigger-list li::before { content: '›'; position: absolute; left: 0; color: var(--org-blue); font-weight: 700; }
.trigger-list li:last-child { border-bottom: none; }
.notes-box { background: var(--paper-dark); border: 1px solid var(--rule); border-left: 4px solid #b8d4d9; padding: 16px 20px; font-size: 13px; color: var(--ink-light); line-height: 1.65; white-space: pre-wrap; }
.notes-empty { font-style: italic; color: var(--ink-muted); }
.p1 { color: var(--critical); font-weight: 700; } .p2 { color: var(--high); font-weight: 700; } .p3 { color: var(--medium); font-weight: 700; }
.copy-btn { font-family: var(--font); font-size: 12px; font-weight: 600; color: var(--org-blue); background: white; border: 1px solid var(--org-blue); padding: 6px 14px; border-radius: 2px; cursor: pointer; transition: background 0.15s, color 0.15s; }
.copy-btn:hover { background: var(--org-blue); color: white; }
.copy-btn-success { background: var(--low-bg) !important; color: var(--low) !important; border-color: var(--low-border) !important; }
.methodology { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; background: var(--paper-dark); border: 1px solid var(--rule); padding: 20px 24px; font-size: 13px; color: var(--ink-light); line-height: 1.6; margin-top: 32px; }
.methodology h4 { font-size: 12px; font-weight: 700; color: var(--ink); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.06em; }
h2 { font-family: Georgia, serif; font-size: 17px; font-weight: 700; color: var(--org-blue); margin: 32px 0 14px; }
h3 { font-family: Georgia, serif; font-size: 14px; font-weight: 700; color: var(--ink); margin: 16px 0 8px; }
@media print { .report-content { padding: 20px; } tr:hover td { background: none; } .copy-btn { display: none; } }
"""

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_header(d):
    m = d["meta"]
    cls = m.get("classification", "INTERNAL").lower()
    cl_label = classification_label(m.get("classification", "INTERNAL"))
    changelog_rows = "".join(
        f'<tr><td>{esc(c["version"])}</td><td>{esc(c["date"])}</td><td>{esc(c["summary"])}</td></tr>'
        for c in m.get("changelog", [])
    )
    return f"""
<div class="classification-banner classification-{cls}">{esc(cl_label)}</div>

<div class="doc-header">
  <div class="doc-header-title">
    <h1 data-id="supplier-title">{esc(m["supplier"])} — Supplier Security Risk Assessment
      <span>For review and decision by the Internal Owner</span>
    </h1>
  </div>
  <div class="doc-meta">
    <strong>Prepared by</strong> Information Security, the organisation<br>
    <strong>Date</strong> {esc(m["date"])}<br>
    <strong>Last reviewed</strong> <span data-id="last-reviewed">{esc(m["last_reviewed"])}</span><br>
    <hr class="meta-divider">
    <strong>Supplier</strong> <span class="supplier-name">{esc(m["supplier"])}</span><br>
    <strong>Service</strong> {esc(m["service"])}<br>
    <strong>Domain</strong> {esc(m["domain"])}<br>
    <strong>Contractual status</strong> {esc(m["contractual_status"])}<br>
    <hr class="meta-divider">
    <strong>Internal owner</strong> {esc(m["internal_owner"])}<br>
    <strong>Risk Assessment Owner</strong> {esc(m["risk_assessment_owner"])}<br>
    <strong>Final Submission date</strong> {esc(m["final_submission_date"])}<br>
    <hr class="meta-divider">
    <strong>Data Classification</strong> {esc(m["data_classification"])}<br>
    <strong>Tier</strong> {esc(tier_label(m.get("tier_num", 1)))}<br>
    <strong>Classification</strong> {esc(m.get("classification", "INTERNAL"))}<br>
    <strong>Version</strong> <span data-id="version">{esc(m["version"])}</span>
  </div>
</div>

<div class="changelog">
  <div class="section-label">Document history</div>
  <table class="changelog-table" data-id="changelog">
    <tr><th>Version</th><th>Date</th><th>Summary of changes</th></tr>
    {changelog_rows}
  </table>
</div>
"""

def build_intro(supplier):
    s = esc(supplier)
    return f"""
<div class="intro">
  <p><strong>What this is.</strong> Our security team has carried out an automated scan and manual
  review of {s}'s externally visible systems. The findings below are things we observed directly
  using our security monitoring tools. We did not need to ask {s} anything to identify them.</p>
  <p><strong>What we need from you.</strong> As the owner of this supplier relationship, you can
  choose to raise these concerns with {s} before the service goes live, or accept the risks as
  they stand. This document exists to make sure the decision is yours, with full information
  in front of you.</p>
</div>
"""

def build_dpia_callout(required):
    if not required:
        return ""
    return """
<div class="notice notice-amber">
  <strong>A Data Protection Impact Assessment (DPIA) is required.</strong> This supplier will
  process personal data on behalf of the organisation. No completed DPIA has been identified for this
  service. Please run the <strong>DPIA skill</strong> to complete one before the service goes live.
</div>
"""

def build_scorecard(d):
    sc = d.get("scorecard", {})
    score = d.get("upguard_score", 0)
    sc_cls = score_colour(score)
    qs = esc(sc.get("questionnaire_status", "Unknown"))
    overall = esc(sc.get("overall_risk", "Unknown"))
    overall_sev = sc.get("overall_risk", "unknown").lower()
    return f"""
<div class="scorecard" data-id="scorecard">
  <div class="score-tile {sc_cls}"><div class="tile-label">UpGuard score</div><div class="tile-value">{score}</div><div class="tile-sub">out of 950</div></div>
  <div class="score-tile tile-critical"><div class="tile-label">Critical</div><div class="tile-value" data-id="count-critical">{sc.get("critical_count",0)}</div><div class="tile-sub">active</div></div>
  <div class="score-tile tile-high"><div class="tile-label">High</div><div class="tile-value" data-id="count-high">{sc.get("high_count",0)}</div><div class="tile-sub">active</div></div>
  <div class="score-tile tile-medium"><div class="tile-label">Medium</div><div class="tile-value" data-id="count-medium">{sc.get("medium_count",0)}</div><div class="tile-sub">active</div></div>
  <div class="score-tile tile-low"><div class="tile-label">Low</div><div class="tile-value" data-id="count-low">{sc.get("low_count",0)}</div><div class="tile-sub">active</div></div>
  <div class="score-tile"><div class="tile-label">Accepted</div><div class="tile-value" data-id="count-accepted">{sc.get("accepted_count",0)}</div><div class="tile-sub">waived</div></div>
  <div class="score-tile"><div class="tile-label">Questionnaire</div><div class="tile-value" style="font-size:13px;padding-top:5px;line-height:1.3;">{qs}</div><div class="tile-sub">status</div></div>
  <div class="score-tile tile-{overall_sev}"><div class="tile-label">Overall risk</div><div class="tile-value" style="font-size:17px;padding-top:4px;" data-id="overall-risk">{overall}</div><div class="tile-sub">highest active</div></div>
</div>
"""

def build_access_management(am):
    items_html = ""
    for item in am.get("items", []):
        items_html += f'<div class="access-item"><div class="access-label">{esc(item["label"])}</div><div class="access-value">{esc(item["value"])}</div></div>'
    grid = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">{items_html}</div>'
    gaps_html = "".join(
        f'<div class="access-gap"><strong>Governance gap:</strong> {esc(g)}</div>'
        for g in am.get("gaps", [])
    )
    return f"<h2>Access Management</h2>{grid}{gaps_html}"

def build_finding_row(f):
    fid    = esc(f["id"])
    sev    = f["severity"]
    row_cls = f"severity-{sev}" if f.get("status") != "resolved" else "row-resolved"
    pb      = prev_badge(f.get("prevalence", ""))
    tkn     = esc(f.get("confirmed_on_org_tenant", False) and " ")
    org_badge = '<span class="prev-badge prev-confirmed-tenant" style="margin-left:3px;">On the organisation tenant</span>' if f.get("confirmed_on_org_tenant") else ""
    sev_cell = f'{badge(sev)}<br><span style="display:inline-block;margin-top:3px;">{pb}{org_badge}</span>'
    tech = esc(f.get("technical_ref", "")).replace("\n", "<br>")
    update = f'<div class="update-note" data-id="update-{fid}">{esc(f["update_note"])}</div>' if f.get("update_note") else ""
    qref = esc(f.get("question_ref", "")) or "—"
    return f"""
<tr class="{row_cls}" data-finding-id="{fid}">
  <td>{sev_cell}</td>
  <td><div class="risk-name">{esc(f["name"])}</div><div class="risk-technical">{tech}</div></td>
  <td class="plain-english">{esc(f["plain_english"])}{update}</td>
  <td>{status_badge(f.get("status","confirmed"))}</td>
  <td class="affects">{tags_html(f.get("affects",[]))}</td>
  <td class="q-ref">{qref}</td>
</tr>"""

def build_findings_table(findings):
    active = [f for f in findings if f.get("status") != "accepted"]
    rows   = "".join(build_finding_row(f) for f in active)
    count  = len([f for f in active if f.get("status") not in ("resolved",)])
    return f"""
<h2>Confirmed Security Findings — {count} active {'issue' if count==1 else 'issues'}</h2>
<table data-id="findings-table" style="margin-bottom:28px;">
  <thead><tr>
    <th style="width:9%">Severity</th>
    <th style="width:20%">Finding</th>
    <th style="width:44%">What this means</th>
    <th style="width:10%">Status</th>
    <th style="width:10%">Affects</th>
    <th style="width:5%">Q</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
"""

def build_accepted_table(accepted):
    if not accepted:
        return ""
    rows = ""
    for a in accepted:
        rows += f"""<tr data-finding-id="{esc(a['id'])}" style="opacity:0.75;">
  <td>{badge(a['severity'])}</td>
  <td><div class="risk-name">{esc(a['name'])}</div><div class="risk-technical">{esc(a.get('technical_ref',''))}</div></td>
  <td class="plain-english">{esc(a.get('description',''))}</td>
  <td><span class="status-badge status-accepted">Accepted</span></td>
  <td style="font-size:12px;color:var(--ink-light);">{esc(a.get('rationale',''))}</td>
</tr>"""
    return f"""
<h2 style="font-size:15px;">Accepted Risks — {len(accepted)} risk{'s' if len(accepted)!=1 else ''} formally accepted</h2>
<table data-id="accepted-table" style="margin-bottom:32px;">
  <thead><tr>
    <th style="width:9%">Severity</th><th style="width:20%">Finding</th>
    <th style="width:35%">Description</th><th style="width:10%">Status</th>
    <th style="width:26%">Acceptance rationale</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""

def build_options(supplier):
    s = esc(supplier)
    return f"""
<h2>Your options</h2>
<div class="options-box">
  <div class="option-card option-a">
    <h3>Option A — Raise with {s}</h3>
    <p>Share the questions below with {s} and ask for written responses and remediation
    timelines before the service goes live. All issues are well understood in the industry
    and a competent technical team should be able to address them. This gives you a documented
    record of their intentions.</p>
  </div>
  <div class="option-card option-b">
    <h3>Option B — Accept the remaining risks</h3>
    <p>Proceed on the basis that the remaining risks are tolerable for your use case. Your
    decision and rationale must be recorded on the risk register. Any Critical findings would
    normally require escalation to director level before acceptance.</p>
  </div>
</div>
"""

def build_question_card(q):
    qid   = esc(q["id"])
    sev   = q.get("severity", "governance")
    tech  = esc(q.get("technical_ref", ""))
    prev  = q.get("prevalence_note", "")
    prev_html = f'<div class="question-prevalence">{esc(prev)}</div>' if prev else ""
    badge_html = f'<span class="badge-gov">Governance</span>' if sev == "governance" else badge(sev)
    resp_html  = q.get("response_block_html", "")  # injected by update script
    return f"""
<div class="question-card severity-{sev}" data-question-id="{qid}">
  <div class="question-header">
    <span class="question-number">{qid}</span>
    <span class="question-title">{esc(q["title"])}</span>
    {badge_html}
    <span class="rt-badge {rt_class(q['response_type'])}">{rt_label(q['response_type'])}</span>
  </div>
  <div class="question-body"><p>{esc(q["body"])}</p></div>
  <div class="question-technical"><span class="tech-label">Technical reference:</span>{tech}</div>
  {prev_html}
  {resp_html}
</div>"""

def build_questions_section(questions, supplier):
    cards = "".join(build_question_card(q) for q in questions)
    s = esc(supplier)
    return f"""
<div class="section-header-row">
  <div class="section-label" style="margin-bottom:0;">Questions for {s}</div>
  <button class="copy-btn" onclick="copyQuestions()" id="copyBtn">Copy all questions</button>
</div>
<p style="font-size:13px;color:var(--ink-light);margin-bottom:18px;line-height:1.6;">
  These questions are written so that a non-technical contact can forward them without interpretation,
  while giving {s}'s technical team all the detail they need to respond.
</p>
<div data-id="questions-container">{cards}</div>
"""

def build_questionnaire_status(text):
    return f"<h2>Questionnaire status</h2><p style='font-size:13.5px;color:var(--ink-light);line-height:1.65;margin-bottom:28px;'>{esc(text)}</p>"

def build_gdpr_section(items):
    if not items:
        return ""
    html = "<h2>Data protection considerations</h2>"
    for item in items:
        html += f'<div class="gdpr-item"><div class="gdpr-label">{esc(item["label"])}</div><div class="gdpr-detail">{esc(item["detail"])}</div></div>'
    return html

def build_fourth_parties(parties, sbom_status, sbom_note, intro_note):
    rows = ""
    for p in parties:
        rows += f'<tr><td>{esc(p.get("name",""))}</td><td>{esc(p.get("role",""))}</td><td>{esc(p.get("data_involved",""))}</td><td>{esc(p.get("location",""))}</td></tr>'
    if not rows:
        rows = '<tr><td colspan="4" style="color:var(--ink-muted);font-style:italic;">Unknown — to be confirmed. See question to supplier.</td></tr>'
    table = f"""<table style="margin-bottom:16px;">
  <thead><tr>
    <th style="width:30%">Organisation</th><th style="width:35%">Role</th>
    <th style="width:20%">Data involved</th><th style="width:15%">Location</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""
    sc = sbom_class(sbom_status)
    sl = sbom_label(sbom_status)
    note = f'<p style="font-size:12.5px;color:var(--ink-light);margin-top:8px;">{esc(sbom_note)}</p>' if sbom_note else ""
    intro = f'<p style="font-size:13px;color:var(--ink-light);line-height:1.65;margin-bottom:14px;">{esc(intro_note)}</p>' if intro_note else ""
    return f"""
<h2>Fourth Parties and Software Supply Chain</h2>
{intro}
{table}
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
  <strong style="font-size:13px;color:var(--ink);">SBOM status:</strong>
  <span class="sbom-status {sc}" data-id="sbom-status">{esc(sl)}</span>
</div>
{note}
"""

def build_actions(actions):
    rows = ""
    for a in actions:
        p = esc(a.get("priority",""))
        pc = priority_class(a.get("priority",""))
        rows += f'<tr><td class="{pc}">{p}</td><td>{esc(a.get("action",""))}</td><td>{esc(a.get("owner",""))}</td><td>{esc(a.get("target",""))}</td></tr>'
    return f"""
<h2>Recommended next steps</h2>
<table style="margin-bottom:32px;">
  <thead><tr>
    <th style="width:8%">Priority</th><th style="width:50%">Action</th>
    <th style="width:24%">Owner</th><th style="width:18%">Target</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""

def build_ongoing_assurance(oa):
    triggers_html = "".join(f'<li>{esc(t)}</li>' for t in oa.get("triggers", []))
    return f"""
<h2>Ongoing Assurance</h2>
<div class="assurance-grid">
  <div class="assurance-tile"><div class="tile-label">Re-assessment frequency</div><div class="tile-value">{esc(oa.get("frequency","Annual"))}</div></div>
  <div class="assurance-tile"><div class="tile-label">Continuous monitoring</div><div class="tile-value">{esc(oa.get("monitoring","UpGuard (live)"))}</div></div>
  <div class="assurance-tile"><div class="tile-label">Next scheduled review</div><div class="tile-value">{esc(oa.get("next_review","To be agreed"))}</div></div>
</div>
<h3>Out-of-cycle review triggers</h3>
<ul class="trigger-list" data-id="triggers">{triggers_html}</ul>
<p style="font-size:12.5px;color:var(--ink-light);margin-top:12px;">
  Responsibility for initiating re-assessment:
  <strong>{esc(oa.get("responsible","Information Security"))}</strong>.
</p>
"""

def build_notes(notes_text):
    if notes_text and notes_text.strip():
        content = f'{esc(notes_text.strip())}'
    else:
        content = '<span class="notes-empty">No additional notes recorded at time of assessment.</span>'
    return f'<h2>Notes</h2><div class="notes-box" data-id="notes">{content}</div>'

def build_methodology(m):
    return f"""
<div class="methodology">
  <div><h4>How we found this</h4>{esc(m.get("how",""))}</div>
  <div><h4>Important context</h4>{esc(m.get("context",""))}</div>
</div>"""

# ---------------------------------------------------------------------------
# Copy-questions JavaScript
# ---------------------------------------------------------------------------
COPY_JS = """
<script>
function copyQuestions() {
  var supplier = document.querySelector('.supplier-name');
  supplier = supplier ? supplier.textContent.trim() : 'Supplier';
  var responseText = {
    'rt-confirm':  'Please confirm this will be addressed and provide an expected completion date.',
    'rt-evidence': 'Please explain the control and provide supporting evidence, such as a policy document, screenshot, or test result.',
    'rt-scope':    'Please confirm whether this applies to the systems used in connection with the organisation, and if not, explain why.'
  };
  var lines = [
    'Questions for ' + supplier + ' -- the organisation Information Security', '',
    'We have completed a routine security review as part of our supplier due diligence process. Please pass the questions below to your technical team and provide responses at your earliest convenience. We are happy to discuss any of these by call if that would be helpful.', ''
  ];
  document.querySelectorAll('.question-card').forEach(function(card) {
    var num   = card.querySelector('.question-number')  ? card.querySelector('.question-number').textContent.trim()  : '';
    var title = card.querySelector('.question-title')   ? card.querySelector('.question-title').textContent.trim()   : '';
    var bodyP = card.querySelector('.question-body p');
    var body  = bodyP ? bodyP.textContent.trim() : '';
    var techEl= card.querySelector('.question-technical');
    var tech  = techEl ? techEl.textContent.replace(/Technical reference:/i,'').trim() : '';
    var prevEl= card.querySelector('.question-prevalence');
    var prev  = prevEl ? prevEl.textContent.trim() : '';
    var rtBadge = card.querySelector('.rt-badge');
    var rtClass = '';
    if (rtBadge) { ['rt-confirm','rt-evidence','rt-scope'].forEach(function(c){ if(rtBadge.classList.contains(c)) rtClass=c; }); }
    var rtText = responseText[rtClass] || '';
    lines.push('---','');
    lines.push(num + ' -- ' + title,'');
    lines.push(body);
    if (tech) { lines.push(''); lines.push('Technical reference: ' + tech); }
    if (prev) { lines.push(''); lines.push(prev); }
    if (rtText){ lines.push(''); lines.push(rtText); }
    lines.push('');
  });
  lines.push('---','','Please reply to the organisation Information Security.','This review was conducted as part of our standard third-party risk management process.');
  var text = lines.join('\\n');
  var btn  = document.getElementById('copyBtn');
  function done() { btn.textContent='Copied!'; btn.classList.add('copy-btn-success'); setTimeout(function(){ btn.textContent='Copy all questions'; btn.classList.remove('copy-btn-success'); },2500); }
  if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(done); }
  else { var ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); done(); }
}
</script>"""

# ---------------------------------------------------------------------------
# Full document assembly
# ---------------------------------------------------------------------------

def generate(d):
    m        = d["meta"]
    supplier = m["supplier"]
    cls_val  = m.get("classification", "INTERNAL")
    date_str = m.get("last_reviewed", m.get("date", ""))

    body = "".join([
        build_header(d),
        build_intro(supplier),
        build_dpia_callout(d.get("dpia_required", False)),
        build_scorecard(d),
        build_access_management(d.get("access_management", {"items": [], "gaps": []})),
        build_findings_table(d.get("findings", [])),
        build_accepted_table(d.get("accepted_risks", [])),
        build_options(supplier),
        build_questions_section(d.get("questions", []), supplier),
        build_questionnaire_status(d.get("questionnaire_status_text", "")),
        build_gdpr_section(d.get("gdpr_items", [])),
        build_fourth_parties(
            d.get("fourth_parties", []),
            d.get("sbom_status", "not_requested"),
            d.get("sbom_note", ""),
            d.get("fourth_parties_note", ""),
        ),
        build_actions(d.get("recommended_actions", [])),
        build_ongoing_assurance(d.get("ongoing_assurance", {})),
        build_notes(d.get("notes", "")),
        build_methodology(d.get("methodology", {})),
    ])

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(supplier)} — Supplier Security Risk Assessment | the organisation</title>
<style>{CSS}</style>
</head>
<body>
<div class="report-page">
  <div class="standalone-header">
    <div>
      <div class="org-name">the organisation</div>
      <div class="doc-type">Third-Party Security Risk Assessment</div>
    </div>
    <div style="font-size:12px;opacity:0.7;text-align:right;">Third-Party Risk Management<br>Information Security</div>
  </div>
  <div class="report-content">{body}</div>
  <div class="standalone-footer">
    <div>the organisation Information Security | {esc(cls_val)} | {esc(date_str)}</div>
    <div class="ai-note">This document has been created with the assistance of AI</div>
  </div>
</div>
{COPY_JS}
</body>
</html>"""

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Generate a the organisation supplier risk assessment HTML report from JSON data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Input JSON schema (assessment_data.json):
  See workflow/03_generate_report.md for the full schema with all required fields.

Example:
  python3 generate_report.py --input assessment_data.json --output acme-risk-assessment.html
""")
    ap.add_argument("--input",  required=True, help="Path to assessment_data.json")
    ap.add_argument("--output", required=True, help="Path to write the HTML report")
    args = ap.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    html = generate(data)
    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"Report written to {output_path} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()
