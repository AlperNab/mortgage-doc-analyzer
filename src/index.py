#!/usr/bin/env python3
"""
mortgage-doc-analyzer — mortgage offer/KFI/ESIS document → fee breakdown,
true cost comparison, red flags, early repayment charges, rate change scenarios
"""
import anthropic, base64, json, re, sys
from pathlib import Path

SYSTEM = """You are an independent mortgage advisor and consumer finance specialist.
Analyze this mortgage document from the BORROWER'S perspective.

Calculate the true total cost, flag every hidden fee and risk, and
help the borrower understand what they're actually signing up for.

Return ONLY valid JSON — no markdown, no explanation.

{
  "document_type": "mortgage_offer|kfi|esis|dip|illustration|other",
  "lender": "string or null",
  "product_name": "string or null",
  "mortgage_type": "repayment|interest_only|part_and_part",
  "rate_type": "fixed|variable|tracker|discounted|offset",
  "key_numbers": {
    "loan_amount": number_or_null,
    "currency": "string",
    "property_value": number_or_null,
    "ltv_pct": number_or_null,
    "initial_rate_pct": number_or_null,
    "initial_rate_period_years": number_or_null,
    "revert_rate_pct": number_or_null,
    "revert_rate_type": "svr|base_rate_plus|libor_plus|other|null",
    "term_years": number_or_null,
    "monthly_payment_initial": number_or_null,
    "monthly_payment_revert": number_or_null,
    "aprc_pct": number_or_null
  },
  "all_fees": [
    {
      "fee_name": "string",
      "amount": number_or_null,
      "when_payable": "upfront|on_completion|on_redemption|monthly|annually",
      "can_be_added_to_loan": true_or_false,
      "mandatory": true_or_false
    }
  ],
  "total_cost_analysis": {
    "total_interest_paid": number_or_null,
    "total_fees": number_or_null,
    "total_cost_of_mortgage": number_or_null,
    "cost_per_month_initial": number_or_null,
    "cost_per_month_revert": number_or_null,
    "break_even_years": number_or_null
  },
  "rate_scenarios": [
    {
      "scenario": "base rate +1%|+2%|+3%",
      "new_monthly_payment": number_or_null,
      "monthly_increase": number_or_null
    }
  ],
  "early_repayment": {
    "erc_applies": true_or_false,
    "erc_period_years": number_or_null,
    "erc_structure": "string or null",
    "erc_max_amount": number_or_null,
    "portable": true_or_false,
    "overpayment_allowed": "unlimited|10pct_pa|other|none",
    "underpayment_allowed": true_or_false
  },
  "red_flags": [
    {
      "issue": "description",
      "severity": "critical|high|medium|low",
      "financial_impact": "string or null",
      "question_to_ask": "what to ask the lender"
    }
  ],
  "green_flags": ["borrower-friendly features"],
  "comparison_checklist": ["things to compare when shopping other lenders"],
  "conditions": ["conditions precedent to mortgage offer being valid"],
  "insurance_requirements": ["buildings","contents","life","critical_illness"],
  "solicitor_notes": ["things your conveyancer should check"],
  "summary": "4-5 sentence plain-English summary of this mortgage offer",
  "verdict": "competitive|average|expensive|avoid",
  "verdict_reason": "one sentence",
  "confidence": 0.0
}"""

def analyze(source: str) -> dict:
    client = anthropic.Anthropic()
    path = Path(source)
    if path.exists() and source.endswith(".pdf"):
        data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        content = [
            {"type":"document","source":{"type":"base64","media_type":"application/pdf","data":data}},
            {"type":"text","text":"Analyze this mortgage document from the borrower's perspective."}
        ]
    elif path.exists():
        text = path.read_text(encoding="utf-8",errors="replace")[:50000]
        content = [{"type":"text","text":f"Analyze this mortgage document:\n\n{text}"}]
    else:
        content = [{"type":"text","text":f"Analyze this mortgage document:\n\n{source[:50000]}"}]

    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=3000, system=SYSTEM,
        messages=[{"role":"user","content":content}]
    )
    raw = re.sub(r'^```(?:json)?\s*','',resp.content[0].text.strip(),flags=re.MULTILINE)
    raw = re.sub(r'\s*```$','',raw,flags=re.MULTILINE)
    return json.loads(raw)

VERDICT_ICON = {"competitive":"✅","average":"🟡","expensive":"🔴","avoid":"🚫"}
SEV_ICON = {"critical":"🚨","high":"🔴","medium":"🟠","low":"🔵"}

def fmt_currency(v, curr=""):
    if v is None: return "N/A"
    return f"{curr}{v:,.0f}"

def print_report(r: dict):
    kn = r.get("key_numbers",{})
    curr = kn.get("currency","")
    tc = r.get("total_cost_analysis",{})
    erc = r.get("early_repayment",{})
    verdict = r.get("verdict","average")

    print(f"\n{'═'*60}")
    print(f"  MORTGAGE ANALYZER — {r.get('lender','?')}")
    print(f"  {r.get('product_name','?')} | {r.get('rate_type','?').upper()} {r.get('mortgage_type','?').upper()}")
    print(f"  Verdict: {VERDICT_ICON.get(verdict,'')} {verdict.upper()} — {r.get('verdict_reason','')}")
    print(f"{'═'*60}")
    print(f"\n  {r.get('summary','')}")

    print(f"\n  KEY NUMBERS")
    if kn.get("loan_amount"): print(f"  Loan:          {fmt_currency(kn['loan_amount'],curr)}")
    if kn.get("ltv_pct"): print(f"  LTV:           {kn['ltv_pct']}%")
    if kn.get("initial_rate_pct"): print(f"  Initial rate:  {kn['initial_rate_pct']}% for {kn.get('initial_rate_period_years','?')} years")
    if kn.get("revert_rate_pct"): print(f"  Reverts to:    {kn['revert_rate_pct']}% ({kn.get('revert_rate_type','')})")
    if kn.get("term_years"): print(f"  Term:          {kn['term_years']} years")
    if kn.get("monthly_payment_initial"): print(f"  Monthly (now): {fmt_currency(kn['monthly_payment_initial'],curr)}/mo")
    if kn.get("monthly_payment_revert"): print(f"  Monthly (svr): {fmt_currency(kn['monthly_payment_revert'],curr)}/mo")
    if kn.get("aprc_pct"): print(f"  APRC:          {kn['aprc_pct']}%")

    fees = r.get("all_fees",[])
    if fees:
        print(f"\n  ALL FEES")
        total_fees = sum(f.get("amount",0) or 0 for f in fees)
        for fee in fees:
            mand = "" if fee.get("mandatory") else " (optional)"
            print(f"  {fee.get('fee_name','?'):<35} {fmt_currency(fee.get('amount'),curr)}{mand}")
        print(f"  {'TOTAL FEES':<35} {fmt_currency(total_fees,curr)}")

    if tc.get("total_cost_of_mortgage"):
        print(f"\n  TOTAL COST OVER TERM: {fmt_currency(tc['total_cost_of_mortgage'],curr)}")
        if tc.get("total_interest_paid"): print(f"  Interest paid: {fmt_currency(tc['total_interest_paid'],curr)}")

    scenarios = r.get("rate_scenarios",[])
    if scenarios:
        print(f"\n  IF RATES RISE")
        for s in scenarios:
            inc = f" (+{fmt_currency(s.get('monthly_increase'),curr)}/mo)" if s.get("monthly_increase") else ""
            print(f"  {s.get('scenario','?'):<20} → {fmt_currency(s.get('new_monthly_payment'),curr)}/mo{inc}")

    print(f"\n  Early repayment charge: {'Yes' if erc.get('erc_applies') else 'No'}", end="")
    if erc.get("erc_period_years"): print(f" for {erc['erc_period_years']} years", end="")
    print()
    if erc.get("overpayment_allowed"): print(f"  Overpayments: {erc['overpayment_allowed']}")

    flags = r.get("red_flags",[])
    if flags:
        sorted_flags = sorted(flags, key=lambda x: ["critical","high","medium","low"].index(x.get("severity","low")))
        print(f"\n  RED FLAGS ({len(flags)})")
        for f in sorted_flags:
            print(f"\n  {SEV_ICON.get(f.get('severity','low'),'')} {f.get('issue','')}")
            if f.get("financial_impact"): print(f"     Impact: {f['financial_impact']}")
            if f.get("question_to_ask"): print(f"     Ask: \"{f['question_to_ask']}\"")

    green = r.get("green_flags",[])
    if green:
        print(f"\n  BORROWER-FRIENDLY FEATURES")
        for g in green: print(f"  ✅ {g}")

    conds = r.get("conditions",[])
    if conds:
        print(f"\n  CONDITIONS TO STAY VALID")
        for c in conds: print(f"  ○ {c}")

    print(f"\n  Confidence: {int(r.get('confidence',0)*100)}%")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    if len(sys.argv)<2: print("Usage: python -m mortgage_doc_analyzer <mortgage.pdf|.txt> [--json]"); sys.exit(0)
    src = sys.argv[1] if sys.argv[1]!="-" else sys.stdin.read()
    r = analyze(src)
    if "--json" in sys.argv: print(json.dumps(r,indent=2,ensure_ascii=False))
    else: print_report(r)
