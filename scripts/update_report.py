#!/usr/bin/env python3
"""
update_report.py — Apply surgical diff updates to an existing risk assessment HTML report.

Uses data-id and data-finding-id / data-question-id attributes embedded by generate_report.py
as anchor points. Does not regenerate the full report; only changed elements are touched.

Usage:
    python3 update_report.py \
        --input existing_report.html \
        --update update_data.json \
        --output updated_report.html
    python3 update_report.py --help
"""

import argparse
import json
import re
import sys
from datetime import datetime
from html import escape as esc
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal DOM-like string operations using data attributes as anchors
# ---------------------------------------------------------------------------

def find_element(html, data_id, tag="*"):
    """Find the outerHTML of an element with data-id='{data_id}'."""
    pattern = rf'(<[a-z][^>]*\bdata-id="{re.escape(data_id)}"[^>]*>)(.*?)(</[a-z]+>)'
    m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    return m

def replace_inner(html, data_id, new_inner):
    """Replace the inner HTML of the element with data-id='{data_id}'."""
    pattern = rf'(<[a-z][^>]*\bdata-id="{re.escape(data_id)}"[^>]*>)(.*?)(</[a-z]+>)'
    replacement = rf'\g<1>{new_inner}\g<3>'
    new_html, n = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return new_html, n > 0

def add_class(html, data_id, cls):
    """Add a CSS class to the element with data-id or data-finding-id '{data_id}'."""
    for attr in ("data-id", "data-finding-id", "data-question-id"):
        pattern = rf'(<[a-z][^>]*)({attr}="{re.escape(data_id)}")([^>]*>)'
        def _add(m, cls=cls):
            tag_open = m.group(1)
            data_attr = m.group(2)
            rest = m.group(3)
            if f' class="' in tag_open:
                tag_open = tag_open.replace(' class="', f' class="{cls} ', 1)
            else:
                tag_open = tag_open + f' class="{cls}"'
            return tag_open + data_attr + rest
        new_html, n = re.subn(pattern, _add, html, count=1, flags=re.DOTALL | re.IGNORECASE)
        if n:
            return new_html, True
    return html, False

def set_attribute(html, data_id, attr_name, attr_value):
    """Set or replace an attribute on element with data-id='{data_id}'."""
    # This is a simple approach: find the tag, set/replace the attribute
    pattern = rf'(<[a-z][^>]*\bdata-id="{re.escape(data_id)}"[^>]*>)'
    def _set(m, attr_name=attr_name, attr_value=attr_value):
        tag = m.group(1)
        # Remove existing attribute if present
        tag = re.sub(rf'\s+{re.escape(attr_name)}="[^"]*"', "", tag)
        # Insert before closing >
        tag = tag.rstrip(">").rstrip() + f' {attr_name}="{esc(attr_value)}">'
        return tag
    new_html, n = re.subn(pattern, _set, html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return new_html, n > 0

def inject_after_element(html, data_finding_id, new_html_chunk):
    """Inject HTML immediately after the closing tag of the element with data-finding-id."""
    pattern = rf'(.*data-finding-id="{re.escape(data_finding_id)}".*?</tr>)'
    replacement = rf'\g<1>\n{new_html_chunk}'
    new_html, n = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return new_html, n > 0

# ---------------------------------------------------------------------------
# Update operations
# ---------------------------------------------------------------------------

def apply_resolved(html, resolved_list):
    """Strike through resolved finding rows and update status badge."""
    for item in resolved_list:
        fid  = item["id"]
        date = item.get("date", "")
        src  = item.get("source", "re-scan")
        note = f'Resolved {date}. Source: {esc(src)}.'
        # Add row-resolved class
        html, _ = add_class(html, fid, "row-resolved")
        # Inject update note after existing content in the plain-english cell
        # (simple: append before </td> in the row — find by data-finding-id)
        update_div = f'<div class="update-note" data-id="update-{fid}">{note}</div>'
        # Replace status badge
        status_pattern = (
            rf'(data-finding-id="{re.escape(fid)}".*?)'
            rf'(<span class="status-badge status-\w+">[^<]+</span>)'
        )
        resolved_badge = '<span class="status-badge status-resolved">Resolved</span>'
        html = re.sub(status_pattern, rf'\g<1>{resolved_badge}',
                      html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return html

def apply_finding_updates(html, updates):
    """Add update notes to finding rows and update status badges."""
    for u in updates:
        fid    = u["id"]
        note   = u.get("update_note", "")
        status = u.get("status", "")
        if note:
            note_div = f'<div class="update-note" data-id="update-{fid}">{esc(note)}</div>'
            # Append after plain-english text
            pattern = rf'(data-finding-id="{re.escape(fid)}".*?class="plain-english"[^>]*>)(.*?)(</td>)'
            html = re.sub(
                pattern,
                rf'\g<1>\g<2>{note_div}\g<3>',
                html, count=1, flags=re.DOTALL | re.IGNORECASE
            )
        if status:
            status_labels = {
                "confirmed": "Confirmed", "partial": "Partial fix", "resolved": "Resolved",
                "accepted": "Accepted", "new": "New", "conflict": "Conflict",
                "unsatisfactory": "Response unsatisfactory",
            }
            label = status_labels.get(status, status)
            badge = f'<span class="status-badge status-{esc(status)}">{esc(label)}</span>'
            pattern = (
                rf'(data-finding-id="{re.escape(fid)}".*?)'
                rf'(<span class="status-badge status-\w+">[^<]+</span>)'
            )
            html = re.sub(pattern, rf'\g<1>{badge}',
                          html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return html

def apply_question_responses(html, responses):
    """Add supplier response blocks to question cards."""
    status_classes = {
        "satisfactory": "ans-satisfactory",
        "partial":      "ans-partial",
        "insufficient": "ans-insufficient",
    }
    status_labels = {
        "satisfactory": "Satisfactory",
        "partial":      "Partial — further information required",
        "insufficient": "Response unsatisfactory",
    }
    for r in responses:
        qid     = r["id"]
        date    = r.get("date", "")
        summary = r.get("summary", "")
        status  = r.get("status", "partial")
        sc      = status_classes.get(status, "ans-partial")
        sl      = status_labels.get(status, status)
        block   = f"""
<div class="question-response">
  <span class="response-label">Supplier response {esc(date)}:</span>
  <span class="rt-badge {esc(sc)}" style="margin-bottom:4px;">{esc(sl)}</span>
  <div style="margin-top:4px;font-size:13px;">{esc(summary)}</div>
</div>"""
        # Append inside the question card (before closing </div>)
        pattern = rf'(data-question-id="{re.escape(qid)}")(.*?)(</div>(?=\s*(?:<div class="question-card|$)))'
        html = re.sub(
            pattern,
            rf'\g<1>\g<2>{block}\g<3>',
            html, count=1, flags=re.DOTALL | re.IGNORECASE
        )
    return html

def append_new_findings(html, new_findings):
    """Append new finding rows to the findings table tbody."""
    if not new_findings:
        return html

    def build_row(f):
        fid  = esc(f["id"])
        sev  = f.get("severity", "medium")
        tags = "".join(f'<span class="tag">{esc(d)}</span>' for d in f.get("affects", []))
        note = f'<div class="update-note">Identified on re-scan {esc(f.get("update_note",""))}.</div>'
        return f"""<tr class="severity-{sev}" data-finding-id="{fid}">
  <td><span class="badge badge-{sev}">{sev.upper()}</span><br>
    <span class="status-badge status-new" style="margin-top:3px;">New</span></td>
  <td><div class="risk-name">{esc(f.get("name",""))}</div>
    <div class="risk-technical">{esc(f.get("technical_ref",""))}</div></td>
  <td class="plain-english">{esc(f.get("plain_english",""))}{note}</td>
  <td><span class="status-badge status-new">New</span></td>
  <td class="affects">{tags}</td>
  <td class="q-ref">{esc(f.get("question_ref","") or "—")}</td>
</tr>"""

    rows_html = "\n".join(build_row(f) for f in new_findings)
    # Append before </tbody> of the findings table (data-id="findings-table")
    pattern = rf'(data-id="findings-table".*?<tbody>)(.*?)(</tbody>)'
    html = re.sub(
        pattern,
        rf'\g<1>\g<2>{rows_html}\g<3>',
        html, count=1, flags=re.DOTALL | re.IGNORECASE
    )
    return html

def append_new_questions(html, new_questions):
    """Append new question cards to the questions container."""
    if not new_questions:
        return html

    from html import escape as esc

    def rt_class(rt):
        return {"confirm":"rt-confirm","evidence":"rt-evidence","scope":"rt-scope"}.get(rt,"rt-confirm")

    def rt_label(rt):
        return {"confirm":"Confirm and fix","evidence":"Explain and evidence","scope":"Clarify scope"}.get(rt,rt)

    cards_html = ""
    for q in new_questions:
        qid  = esc(q["id"])
        sev  = q.get("severity","governance")
        prev = f'<div class="question-prevalence">{esc(q["prevalence_note"])}</div>' if q.get("prevalence_note") else ""
        badge_html = f'<span class="badge-gov">Governance</span>' if sev=="governance" else f'<span class="badge badge-{sev}">{sev.upper()}</span>'
        cards_html += f"""
<div class="question-card severity-{sev}" data-question-id="{qid}">
  <div class="question-header">
    <span class="question-number">{qid}</span>
    <span class="question-title">{esc(q["title"])}</span>
    {badge_html}
    <span class="rt-badge {rt_class(q['response_type'])}">{rt_label(q['response_type'])}</span>
  </div>
  <div class="question-body"><p>{esc(q["body"])}</p></div>
  <div class="question-technical"><span class="tech-label">Technical reference:</span>{esc(q.get("technical_ref",""))}</div>
  {prev}
</div>"""

    # Append inside questions container
    pattern = rf'(data-id="questions-container")(.*?)(</div>(?=\s*\n?\s*<h2))'
    html = re.sub(
        pattern,
        rf'\g<1>\g<2>{cards_html}\g<3>',
        html, count=1, flags=re.DOTALL | re.IGNORECASE
    )
    return html

def update_changelog(html, entry):
    """Append a new row to the changelog table."""
    row = f'<tr><td>{esc(entry["version"])}</td><td>{esc(entry["date"])}</td><td>{esc(entry["summary"])}</td></tr>'
    pattern = rf'(data-id="changelog".*?<tbody>)(.*?)(</tbody>)'
    # If no tbody, append before </table>
    if not re.search(r'<tbody>', html[html.find('data-id="changelog"'):html.find('data-id="changelog"')+2000]):
        pattern = rf'(data-id="changelog".*?)(</table>)'
        html = re.sub(pattern, rf'\g<1>{row}\g<2>', html, count=1, flags=re.DOTALL | re.IGNORECASE)
    else:
        html = re.sub(pattern, rf'\g<1>\g<2>{row}\g<3>', html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return html

def update_meta_field(html, data_id, new_value):
    """Update the text content of an element identified by data-id."""
    pattern = rf'(<[^>]*\bdata-id="{re.escape(data_id)}"[^>]*>)([^<]*)(<)'
    html = re.sub(pattern, rf'\g<1>{esc(new_value)}\g<3>', html, count=1, flags=re.DOTALL)
    return html

# ---------------------------------------------------------------------------
# Accepted risks, notes, and scorecard (previously hand-edited; now scripted)
# ---------------------------------------------------------------------------

ACCEPTED_SECTION_TEMPLATE = (
    '\n<h2 style="font-size:15px;">Accepted Risks: formally accepted</h2>\n'
    '<table data-id="accepted-table" style="margin-bottom:32px;">\n'
    '  <thead><tr>\n'
    '    <th style="width:9%">Severity</th><th style="width:20%">Finding</th>\n'
    '    <th style="width:35%">Description</th><th style="width:10%">Status</th>\n'
    '    <th style="width:26%">Acceptance rationale</th>\n'
    '  </tr></thead>\n'
    '  <tbody></tbody>\n'
    '</table>'
)

def adjust_count(html, data_id, delta):
    """Add delta to the integer shown in the scorecard tile with this data-id."""
    pattern = rf'(<[^>]*\bdata-id="{re.escape(data_id)}"[^>]*>)(\s*)(\d+)(\s*<)'
    def _adj(m):
        n = max(0, int(m.group(3)) + delta)
        return f'{m.group(1)}{m.group(2)}{n}{m.group(4)}'
    new_html, _ = re.subn(pattern, _adj, html, count=1, flags=re.DOTALL)
    return new_html

def apply_accepted(html, accepted_list):
    """Move each accepted finding from the findings table to the Accepted Risks
    table, creating that table if the report had no accepted risks at generation,
    and adjust the scorecard. Returns (html, moved_count)."""
    moved = 0
    for a in accepted_list:
        fid = a["id"]
        row_m = re.search(rf'<tr\b[^>]*data-finding-id="{re.escape(fid)}"[^>]*>.*?</tr>',
                          html, re.DOTALL | re.IGNORECASE)
        if not row_m:
            continue  # not in the findings table (already accepted or unknown)
        row = row_m.group(0)
        sev_m = re.search(r'class="severity-(\w+)"', row) or re.search(r'badge-(\w+)"', row)
        sev = sev_m.group(1) if sev_m else "medium"
        name = (re.search(r'class="risk-name">(.*?)</div>', row, re.DOTALL) or [None, fid])[1]
        tech = (re.search(r'class="risk-technical">(.*?)</div>', row, re.DOTALL) or [None, ""])[1]
        pe_m = re.search(r'class="plain-english">(.*?)</td>', row, re.DOTALL)
        pe = pe_m.group(1) if pe_m else ""
        pe = re.sub(r'<div class="update-note".*?</div>', "", pe, flags=re.DOTALL).strip()

        # remove the row from the findings table
        html = html[:row_m.start()] + html[row_m.end():]

        # create the Accepted Risks section if it does not exist yet
        if 'data-id="accepted-table"' not in html:
            ft = re.search(r'data-id="findings-table".*?</table>', html, re.DOTALL | re.IGNORECASE)
            if ft:
                html = html[:ft.end()] + ACCEPTED_SECTION_TEMPLATE + html[ft.end():]

        rationale = esc(a.get("rationale", "")) or "No rationale recorded."
        acc_row = (
            f'<tr data-finding-id="{esc(fid)}" style="opacity:0.75;">\n'
            f'  <td><span class="badge badge-{sev}">{sev.upper()}</span></td>\n'
            f'  <td><div class="risk-name">{name}</div><div class="risk-technical">{tech}</div></td>\n'
            f'  <td class="plain-english">{pe}</td>\n'
            f'  <td><span class="status-badge status-accepted">Accepted</span></td>\n'
            f'  <td style="font-size:12px;color:var(--ink-light);">{rationale}</td>\n'
            f'</tr>'
        )
        html, _ = re.subn(r'(data-id="accepted-table".*?<tbody>)(.*?)(</tbody>)',
                          lambda m: m.group(1) + m.group(2) + acc_row + m.group(3),
                          html, count=1, flags=re.DOTALL | re.IGNORECASE)

        html = adjust_count(html, f"count-{sev}", -1)
        html = adjust_count(html, "count-accepted", +1)
        moved += 1
    return html, moved

def apply_notes(html, notes_text):
    """Replace the contents of the notes box (data-id='notes')."""
    if notes_text and notes_text.strip():
        inner = esc(notes_text.strip())
    else:
        inner = '<span class="notes-empty">No additional notes recorded.</span>'
    pattern = r'(<div[^>]*\bdata-id="notes"[^>]*>).*?(</div>)'
    new_html, _ = re.subn(pattern, lambda m: m.group(1) + inner + m.group(2),
                          html, count=1, flags=re.DOTALL)
    return new_html

def apply_scorecard_override(html, ov):
    """Apply an explicit assessor decision to the scorecard tiles."""
    for key, did in (("critical_count", "count-critical"), ("high_count", "count-high"),
                     ("medium_count", "count-medium"), ("low_count", "count-low"),
                     ("accepted_count", "count-accepted")):
        if key in ov:
            html = update_meta_field(html, did, str(ov[key]))
    if ov.get("overall"):
        html = update_meta_field(html, "overall-risk", ov["overall"])
    return html

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Apply surgical diff updates to an existing risk assessment HTML report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
update_data.json schema:
{
  "meta_updates": {
    "version": "1.1",
    "last_reviewed": "YYYY-MM-DD",
    "changelog_entry": {"version": "1.1", "date": "YYYY-MM-DD", "summary": "..."}
  },
  "resolved": [{"id": "F001", "date": "YYYY-MM-DD", "source": "re-scan"}],
  "new_findings": [{...}],                  // full finding objects
  "accepted": [{"id": "F003", "rationale": "..."}],  // moved to Accepted Risks table, scorecard adjusted
  "notes": "Free text for the notes box, or null to leave unchanged",
  "scorecard_override": {"overall": "High", "high_count": 2}  // explicit assessor decision
  "finding_updates": [{"id": "F002", "status": "partial", "update_note": "..."}],
  "question_responses": [{"id": "Q1", "date": "...", "summary": "...", "status": "satisfactory"}],
  "new_questions": [{...}]                  // full question objects
}

Example:
  python3 update_report.py --input report.html --update update_data.json --output report.html
""")
    ap.add_argument("--input",  required=True, help="Existing HTML report")
    ap.add_argument("--update", required=True, help="Update JSON file")
    ap.add_argument("--output", required=True, help="Output HTML path (can be same as input)")
    args = ap.parse_args()

    html   = Path(args.input).read_text(encoding="utf-8")
    update = json.loads(Path(args.update).read_text(encoding="utf-8"))

    # 1. Meta updates
    mu = update.get("meta_updates", {})
    if mu.get("version"):
        html = update_meta_field(html, "version", mu["version"])
    if mu.get("last_reviewed"):
        html = update_meta_field(html, "last-reviewed", mu["last_reviewed"])
    if mu.get("changelog_entry"):
        html = update_changelog(html, mu["changelog_entry"])

    # 2. Resolved findings
    html = apply_resolved(html, update.get("resolved", []))

    # 3. Finding updates (status + note)
    html = apply_finding_updates(html, update.get("finding_updates", []))

    # 4. New findings
    html = append_new_findings(html, update.get("new_findings", []))

    # 5. Question responses
    html = apply_question_responses(html, update.get("question_responses", []))

    # 6. New questions
    html = append_new_questions(html, update.get("new_questions", []))

    # 7. Accepted findings: move to the Accepted Risks table and adjust the scorecard
    accepted_moved = 0
    if update.get("accepted"):
        html, accepted_moved = apply_accepted(html, update["accepted"])

    # 8. Notes box
    if "notes" in update and update["notes"] is not None:
        html = apply_notes(html, update["notes"])

    # 9. Explicit scorecard override (assessor decision)
    if update.get("scorecard_override"):
        html = apply_scorecard_override(html, update["scorecard_override"])

    Path(args.output).write_text(html, encoding="utf-8")

    total_changes = (
        len(update.get("resolved", [])) +
        len(update.get("finding_updates", [])) +
        len(update.get("new_findings", [])) +
        len(update.get("question_responses", [])) +
        len(update.get("new_questions", [])) +
        accepted_moved
    )
    print(f"Applied {total_changes} change(s) to report.")
    print(f"Output: {args.output}")
    if accepted_moved:
        print(f"Moved {accepted_moved} finding(s) to the Accepted Risks table and adjusted the scorecard.")

if __name__ == "__main__":
    main()
