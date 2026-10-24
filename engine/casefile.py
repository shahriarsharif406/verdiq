"""Auditor Case File: Markdown (+PDF) per flagged item. Optional LLM-written summary; always falls back to template text."""
from __future__ import annotations

import os
from datetime import date

from . import merkle
from .common import SEV_RANK, fmt_serial, overlap

ACTIONS = {
    "R01": "Freeze the second buyer's position, contact the seller for explanation, notify the registry. Treat the first sale as the valid one.",
    "R02": "Reject the second retirement claim; require the claimant to withdraw the duplicate public claim.",
    "R03": "Quarantine the serials, request the registry's issuance record, and report the counterparty if issuance cannot be evidenced.",
    "R04": "Suspend issuance for both projects pending a land-title and boundary audit; require a single beneficiary for the overlapping area.",
    "R05": "Hold the vintage's credits; request biomass inventory, remote-sensing evidence and a verifier re-assessment.",
    "R06": "Require the host country and the buyer to agree on who claims the tonnes; apply or withdraw the corresponding adjustment.",
    "R07": "Open a market-abuse review of the trading desks involved; exclude the circular volume from price discovery.",
    "R08": "Request trade documentation and counterparty confirmation for the abnormally priced trade.",
    "R09": "Ask the company to correct or substantiate the public claim; flag the gap to advertising / sustainability-claims regulators.",
    "R10": "Reject the sale (seller never held the credits) and investigate the seller's source of supply.",
    "R11": "Reject the transaction; the actor does not hold the credits.",
}


def _llm_summary(facts: str) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic  # optional dependency

        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.environ.get("VERDIQ_LLM_MODEL", "claude-haiku-5-5"), max_tokens=400,
            messages=[{"role": "user", "content": "Write a 3-sentence plain-English audit summary for a carbon-market auditor. Use ONLY these facts; "
                       "do not add numbers or names that are not present.\n\n" + facts}])
        return msg.content[0].text.strip()
    except Exception:
        return None


def template_summary(f: dict) -> str:
    tail = f" Estimated value at risk: ${f['usd_at_risk']:,.0f}." if f["usd_at_risk"] else ""
    return (f"Rule {f['rule_id']} ({f['rule_name'].replace('_', ' ').title()}, {f['severity']}) fired on {f['subject_type']} {f['subject_id']}"
            f"{' in project ' + f['project_id'] if f.get('project_id') else ''}, covering {f['tco2']:,} tCO2. {f['reason']}{tail}")


def build_markdown(res, f: dict, tx_index: dict | None = None, anchors: dict | None = None, use_llm: bool = True) -> tuple[str, str]:
    """Returns (markdown, summary_source) where summary_source is 'llm' or 'template'."""
    tx_index, anchors = tx_index or {}, anchors or {}
    facts = template_summary(f)
    summary, src = (_llm_summary(facts) if use_llm else None), "llm"
    if not summary:
        summary, src = facts, "template"

    ev = res.events
    related = ev[[False] * len(ev)]
    if f["ranges"]:
        mask = ev.apply(lambda r: any(overlap(int(r.serial_start), int(r.serial_end), a, b) for a, b in f["ranges"]), axis=1)
        related = ev[mask].sort_values("date")
    L = [f"# Case file · {f['rule_id']} · {f['subject_id']}", "",
         f"*Generated {date.today().isoformat()} by VERDIQ · all data synthetic · summary source: **{src}***", "",
         "## 1. Summary", summary, "",
         "## 2. Finding",
         f"| field | value |\n|---|---|\n| Rule | `{f['rule_id']}` {f['rule_name']} |\n| Severity | **{f['severity']}** |\n| Subject | {f['subject_type']} `{f['subject_id']}` |\n"
         f"| Project | {f.get('project_id') or '-'} |\n| Tonnes | {f['tco2']:,} tCO2 |\n| Value at risk | ${f['usd_at_risk']:,.0f} |\n"
         f"| Serials | {', '.join(f'{fmt_serial(a)} to {fmt_serial(b)}' for a, b in f['ranges'][:4]) or '-'} |",
         "", f"**Why:** {f['reason']}", "", "## 3. Timeline of ledger activity on these serials"]
    if len(related):
        L += ["| date | id | kind | actor | counterparty | tCO2 | engine status | on-chain |", "|---|---|---|---|---|---|---|---|"]
        for r in related.head(25).itertuples():
            tx = tx_index.get(r.event_id)
            chain_s = "-" if not tx else ("accepted" if tx["ok"] else f"REVERTED {tx['reason']}")
            L.append(f"| {r.date} | {r.event_id} | {r.kind} | {r.actor} | {r.counterparty} | {r.tco2:,} | {r.status} | {chain_s} |")
    else:
        L.append("No trade or retirement overlaps these serials (project-level finding).")
    L += ["", "## 4. Evidence rows"]
    if f["evidence"]:
        keys = sorted({k for e in f["evidence"] for k in e})
        L += ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
        for e in f["evidence"]:
            L.append("| " + " | ".join(str(e.get(k, "")) for k in keys) + " |")
    else:
        L.append("No additional evidence rows.")
    L += ["", "## 5. Blocking transaction"]
    tx = tx_index.get(f["subject_id"])
    if tx and not tx["ok"]:
        L += [f"The VerdiqRegistry contract **reverted** this transaction.", "", f"- reason code: `{tx['reason']}`", f"- tx hash: `{tx['txHash']}`",
              f"- block: {tx['block']}  ·  gas used: {tx['gasUsed']:,}"]
    elif tx:
        L += [f"On-chain the transaction was accepted (the contract enforces ownership and uniqueness; this finding is behavioural / statistical). tx `{tx['txHash']}`."]
    else:
        L += ["No on-chain transaction is associated with this finding (project-level, statistical or off-chain claim). Run `make replay` to attach chain evidence."]
    L += ["", "## 6. Merkle proof (Day-End Close)"]
    closes = sorted(res.closes)
    cd = next((d for d in closes if d >= (f.get("date") or "")), closes[-1])
    close = res.closes[cd]
    probe = f["ranges"][0][0] if f["ranges"] else None
    pr = merkle.proof_for_serial(close, probe) if probe else None
    if pr:
        anc = anchors.get(cd)
        L += [f"Close of **{cd}** · root `{close['root']}`" + (f" · anchored in tx `{anc['txHash']}` (block {anc['block']})" if anc else ""), "",
              f"- leaf #{pr['index']} (`{pr['leaf']}`), status **{pr['record']['status']}**, rules {pr['record']['rules']}",
              f"- proof valid: **{merkle.verify_proof(pr)}**", "- path:"] + [f"  - `{p}`" for p in pr["path"]]
    else:
        L.append(f"These serials have no segment in the {cd} snapshot: they were never issued, so the Merkle tree provides a *non-membership* signal.")
    L += ["", "## 7. Recommended action", ACTIONS.get(f["rule_id"], "Review manually."), "",
          "---", "*Synthetic demonstration data. Not an accusation against any real entity.*"]
    return "\n".join(L), src


def to_pdf(markdown: str) -> bytes:
    from fpdf import FPDF

    def clean(s: str) -> str:
        rep = {"→": "->", "•": "-", "“": '"', "”": '"', "’": "'", "₂": "2", "×": "x", "…": "...", "—": "-", "–": "-"}
        for k, v in rep.items():
            s = s.replace(k, v)
        return s.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(True, 14)
    pdf.add_page()
    pdf.set_fill_color(6, 19, 15)
    pdf.rect(0, 0, 210, 22, "F")
    pdf.set_text_color(245, 196, 81)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 7)
    pdf.cell(0, 8, "VERDIQ  |  Auditor Case File")
    pdf.set_text_color(20, 20, 20)
    pdf.set_xy(10, 28)
    for raw in markdown.splitlines():
        line = clean(raw.replace("**", "").replace("`", "").replace("*", ""))
        pdf.set_x(10)
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 14); pdf.multi_cell(190, 7, line[2:])
        elif line.startswith("## "):
            pdf.ln(2); pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(5, 120, 85); pdf.multi_cell(190, 6, line[3:]); pdf.set_text_color(20, 20, 20)
        elif line.startswith("|---") or not line.strip():
            pdf.ln(1)
        elif line.startswith("|"):
            pdf.set_font("Courier", "", 7); pdf.multi_cell(190, 3.6, line.strip("|").replace("|", "  |  "))
        else:
            pdf.set_font("Helvetica", "", 9.5); pdf.multi_cell(190, 4.8, line)
    return bytes(pdf.output())
