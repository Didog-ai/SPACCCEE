"""Build the QLD dealer sales pack from prospects.json.

Outputs (in research/qld/out/):
  catalogues/<id>.html   dealer-facing range proposal (rendered to PDF by render_pdfs.mjs)
  emails.json            meeting-request email per dealer
  qld_prospects.csv      import into the bot's CRM: python -m sales_bot import research/qld/out/qld_prospects.csv
  sales-pack.html        internal page: every prospect, how to sell to them, the email, the call-only list
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = json.loads((HERE / "prospects.json").read_text(encoding="utf-8"))

# Indicative Innovatix range. Final spec, ATM and pricing are confirmed on quote.
MODELS = {
    "BX64":  ("6x4 Box Trailer", "Single axle", "1830 x 1220 mm deck, 300 mm sides", "750 kg", "The everyday domestic seller."),
    "BX74":  ("7x4 Box Trailer", "Single axle", "2130 x 1220 mm deck, 300 mm sides", "750 kg", "Highest-volume size for most yards."),
    "BX75":  ("7x5 Box Trailer", "Single axle", "2130 x 1520 mm deck, 300 mm sides", "750 kg", "Wider deck for garden and tip runs."),
    "BX85":  ("8x5 Box Trailer", "Single axle", "2440 x 1520 mm deck, 300 mm sides", "750 kg", "Popular all-rounder."),
    "BX85H": ("8x5 Heavy-Duty Box", "Single axle, braked", "2440 x 1520 mm deck, 400 mm sides", "1400 kg", "For trades and farm work."),
    "BX86H": ("8x6 Heavy-Duty Box", "Single axle, braked", "2440 x 1830 mm deck, 400 mm sides", "1400 kg", "Big-volume single axle."),
    "CG74":  ("7x4 Cage Trailer", "Single axle", "2130 x 1220 mm deck, 600 mm mesh cage", "750 kg", "Green waste and household loads."),
    "CG85":  ("8x5 Cage Trailer", "Single axle, tilt", "2440 x 1520 mm deck, 900 mm mesh cage", "750 kg", "High cage for bulky, light loads."),
    "CG85T": ("8x5 Tipping Cage Trailer", "Single axle, manual tip", "2440 x 1520 mm deck, 600 or 900 mm cage", "750 kg", "Tip-and-go for landscapers."),
    "TD85":  ("8x5 Tandem Box", "Tandem axle, braked", "2440 x 1520 mm deck, 400 mm sides", "2000 kg", "Stable, heavier payloads."),
    "TD105": ("10x5 Tandem Box / Cage", "Tandem axle, braked", "3050 x 1520 mm deck, cage optional", "2000 kg", "The trade workhorse."),
    "TD126": ("12x6 Tandem Cage", "Tandem axle, electric brakes", "3660 x 1830 mm deck, 600 mm cage", "3500 kg", "Maximum legal light-trailer payload."),
    "TR105": ("10x5 Tradesman / Builders", "Tandem axle, braked", "3050 x 1520 mm, ladder racks, lockable toolbox", "2000 kg", "Builders, plumbers, sparkies."),
    "CC45":  ("Car Carrier, 4.5 m deck", "Tandem axle, braked", "Beaver tail, slide-out ramps, winch plate", "up to 3500 kg", "Car yards, mechanics, motorsport."),
    "PL35":  ("Plant Trailer 3.5 x 1.8 m", "Tandem axle, electric brakes", "Fold-up ramps, tie-down points", "3500 kg", "Mini excavators and skid steers."),
    "TP85":  ("8x5 Hydraulic Tipper", "Tandem axle, braked", "Electric-hydraulic tipping body", "2000 kg", "Soil, gravel and green waste."),
    "TP106": ("10x6 Hydraulic Tipper", "Tandem axle, electric brakes", "Electric-hydraulic tipping body, 600 mm sides", "3500 kg", "Civil and landscaping crews."),
    "FT106": ("10x6 Flat Top / Drop Side", "Tandem axle, electric brakes", "Drop sides, rated tie-downs", "3500 kg", "Pallets, machinery, farm loads."),
    "ATV85": ("8x5 ATV / Mower Trailer", "Single axle", "Full-width fold-down ramp, tilt body", "750 kg (1400 kg braked option)", "Mowers, quads and side-by-sides."),
    "VAN74": ("7x4 Enclosed Van Trailer", "Single axle", "Lockable, rear barn doors", "750 kg", "Secure storage for trades and events."),
    "BT55":  ("Galvanised Boat Trailer", "Single or tandem axle", "Multi-roller, boats to 5.5 m", "750-1400 kg", "Salt-water ready."),
    "OR75":  ("7x5 Off-Road Box", "Single axle, braked", "Heavy-duty springs, off-road coupling", "1400 kg", "Built for outback tracks."),
    "LS85":  ("8x5 Stock Crate Trailer", "Tandem axle, braked", "Galvanised crate, rear ramp", "2000 kg", "Small livestock and farm moves."),
    "CHS":   ("Rolling Chassis / Flat-Pack Kit", "Any size 6x4 to 12x6", "Galvanised chassis, drawbar and axle mounts, built to your drawings", "to suit", "Finish and badge them in your own workshop."),
    "CAGE":  ("Cages and Sub-Assemblies", "Made to order", "Mesh cages, drawbars, ramps, tailgates", "n/a", "Extra fabrication capacity."),
}

WHY_DEALER = [
    ("Certified steel", "Mill certificates and welder certifications supplied, so you can check the steel and the welds yourself."),
    ("Fully hot-dip galvanised", "Every complete trailer is fully galvanised for Queensland's coast and conditions."),
    ("Built to Australian rules", "Built to the Australian Design Rules (ADRs) and supplied with a VIN."),
    ("Factory-direct price", "Our own factory, no trader in between. Landed below comparable imports."),
    ("Pay as you sell", "Flexible credit terms: you can pay for trailers as they sell."),
    ("Low-risk start", "Mixed-model containers, a trial container, or a sample unit to inspect first."),
    ("Your spec, your brand", "We build to your drawings and can supply under your own brand."),
]
WHY_BUILDER = [
    ("Extra capacity", "Galvanised chassis, sub-assemblies or standard sizes built to your drawings."),
    ("Certified steel", "Mill certificates and welder certifications supplied with every batch."),
    ("Your brand stays yours", "Supplied unbranded or under a separate value brand, so your own line is untouched."),
    ("Built to Australian rules", "Complete trailers built to the ADRs and supplied with a VIN."),
    ("Flexible terms", "Mixed loads and flexible credit terms."),
]
STEPS = [
    ("Choose your mix", "Pick models and quantities for one container. Mixed loads are fine."),
    ("We build and ship", "Built and galvanised in our factory, flat-packed to fit more trailers per container."),
    ("Assemble and sell", "Assembly guide supplied. Parts and warranty support in Australia."),
    ("Pay as they sell", "Flexible credit terms agreed up front."),
]


def esc(s) -> str:
    return html.escape(str(s or ""))


# ---- email -------------------------------------------------------------------

def email_for(p: dict) -> dict:
    first = p.get("contact_name", "") or ""
    greet = f"Hi {first.split(' ')[0]}," if first and not first.startswith("(") else f"Hi {p['company'].split(' (')[0]} team,"
    if p["tier"] == 3:
        subject = f"Fabrication capacity for {p['company'].split(' (')[0]}: quick chat?"
        bullets = [
            "Galvanised chassis, sub-assemblies or complete standard trailers built to your drawings",
            "Certified steel and welds, with mill certificates and welder certifications supplied",
            "Built to ADRs and VIN-plated when supplied as complete trailers",
            "Supplied unbranded or under a separate brand, so your Australian-made line stays separate",
            "Mixed loads and flexible credit terms",
        ]
        lead = "Here's what we can offer a builder like you:"
        intro = ("I'm with Innovatix. We're a steel fabrication company with our own factory in India, "
                 "and we supply galvanised trailers and components to Queensland trailer businesses.")
    else:
        subject = f"Galvanised trailer supply for {p['company'].split(' (')[0]}: 30-minute meeting?"
        intro = ("I'm with Innovatix. We're a steel fabrication company with our own factory in India, and we build "
                 "fully hot-dip galvanised trailers that ship flat-packed to Australian dealers. Several Queensland "
                 "dealers already stock our range, and the response has been very strong.")
        if p["id"] in ("wide-bay", "toowoomba-trailers"):
            lead = "Here's why dealers are moving their imported range to us:"
        elif p["tier"] == 1:
            lead = "If some of your range comes from Chinese suppliers, here's why dealers are moving that volume to us:"
        else:
            lead = "Here's why dealers are adding us as a second supplier:"
        bullets = [
            "Higher-grade, certified steel: we supply mill certificates and welder certifications so you can check it yourself",
            "Fully hot-dip galvanised, built to ADRs and VIN-plated",
            "Factory-direct pricing, landed below comparable Chinese imports",
            "Flexible credit terms: you can pay as the trailers sell",
            "Mixed-model containers and a trial container, so you can test us without the risk",
            "Dependable lead times straight from our own factory, with no trader in the middle",
            "Built to your spec, or under your own brand",
        ]
    body = "\n".join([
        greet, "",
        p["opener"], "",
        intro, "",
        lead,
        *[f"- {b}" for b in bullets], "",
        f"I've attached a short range proposal built around the {p['range_line']} you already sell.", "",
        f"Could we find 30 minutes in the next couple of weeks? I'm happy to meet {p['meeting']} and bring a weld "
        "cut-section and our mill certificates so you can see the build quality first-hand. Would Tuesday 1 or "
        "Thursday 3 December work, or is there a better time for you?", "",
        "Kind regards,",
    ])
    html_body = (
        f"<p>{esc(greet)}</p><p>{esc(p['opener'])}</p><p>{esc(intro)}</p><p>{esc(lead)}</p><ul>"
        + "".join(f"<li>{esc(b)}</li>" for b in bullets)
        + f"</ul><p>I've attached a short range proposal built around the {esc(p['range_line'])} you already sell.</p>"
        f"<p>Could we find 30 minutes in the next couple of weeks? I'm happy to meet {esc(p['meeting'])} and bring a "
        "weld cut-section and our mill certificates so you can see the build quality first-hand. Would Tuesday 1 or "
        "Thursday 3 December work, or is there a better time for you?</p><p>Kind regards,</p>"
    )
    return {"id": p["id"], "to": p.get("email"), "subject": subject, "body": body, "html": html_body,
            "attachment": f"Innovatix-Range-{p['id']}.pdf"}


# ---- dealer catalogue -----------------------------------------------------------

CAT_CSS = """
@page { size: A4; margin: 0; }
:root { --ink:#16232d; --steel:#2f4f63; --zinc:#e6eaed; --zinc2:#c9d1d6; --muted:#5d6b75; --mark:#d98a1e; }
* { box-sizing: border-box; }
body { margin:0; font-family: Inter, 'Liberation Sans', sans-serif; color: var(--ink); font-size: 10pt; line-height: 1.45; }
.page { width: 210mm; min-height: 297mm; padding: 16mm 16mm 14mm; position: relative; page-break-after: always; }
.page:last-child { page-break-after: auto; }
h1, h2, h3 { font-family: 'Inter Display', Inter, sans-serif; margin: 0; letter-spacing: -0.01em; text-wrap: balance; }
.mono { font-family: 'JetBrains Mono', monospace; }
.cover { background: var(--ink); color: #fff; padding: 0; display: flex; flex-direction: column; }
.cover .top { padding: 18mm 16mm 0; }
.brand { font-family: 'Inter Display'; font-weight: 800; font-size: 13pt; letter-spacing: .22em; }
.brand span { color: var(--mark); }
.cover h1 { font-size: 34pt; line-height: 1.05; font-weight: 800; margin-top: 46mm; max-width: 150mm; }
.cover .for { margin-top: 8mm; font-size: 13pt; color: #c5d3dc; }
.cover .for b { color:#fff; }
.spangle { margin-top: auto; height: 78mm; background:
  repeating-linear-gradient(115deg, rgba(255,255,255,.05) 0 9mm, rgba(255,255,255,0) 9mm 19mm),
  repeating-linear-gradient(35deg, rgba(255,255,255,.04) 0 6mm, rgba(255,255,255,0) 6mm 15mm),
  linear-gradient(160deg, #6f8594, #a9b8c1 45%, #7d929f); position: relative; }
.spangle .plate { position:absolute; left:16mm; bottom:14mm; background: #f4f6f7; color: var(--ink); border-radius: 2mm;
  padding: 5mm 6mm; width: 92mm; box-shadow: 0 1mm 3mm rgba(0,0,0,.25); }
.plate .row { display:flex; justify-content: space-between; font-family:'JetBrains Mono'; font-size: 8.5pt; padding: 1mm 0; border-bottom: .2mm solid var(--zinc2); }
.plate .row:last-child { border-bottom: 0; }
.plate .hd { font-family:'Inter Display'; font-weight:700; font-size: 8pt; letter-spacing:.16em; color: var(--muted); margin-bottom: 1.5mm; }
.eyebrow { font-size: 8pt; letter-spacing: .18em; text-transform: uppercase; color: var(--steel); font-weight: 700; }
h2 { font-size: 20pt; font-weight: 800; margin: 2mm 0 6mm; }
.why { display:grid; grid-template-columns: 1fr 1fr; gap: 5mm 8mm; }
.why div b { display:block; font-family:'Inter Display'; font-size: 11pt; margin-bottom: 1mm; }
.why div { border-top: .6mm solid var(--ink); padding-top: 2.5mm; }
.note { margin-top: 8mm; background: var(--zinc); padding: 5mm 6mm; border-radius: 1.5mm; }
.note b { font-family:'Inter Display'; }
table { width:100%; border-collapse: collapse; }
th { text-align:left; font-size: 7.5pt; letter-spacing:.14em; text-transform: uppercase; color: var(--muted); padding: 0 2mm 2mm; border-bottom: .5mm solid var(--ink); }
td { padding: 3mm 2mm; border-bottom: .2mm solid var(--zinc2); vertical-align: top; }
td.code { font-family:'JetBrains Mono'; font-size: 8.5pt; color: var(--steel); white-space: nowrap; }
td.atm { font-family:'JetBrains Mono'; font-size: 8.5pt; white-space: nowrap; }
td .nm { font-weight: 700; }
td .sub { color: var(--muted); font-size: 8.5pt; }
.steps { display:grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin-top: 4mm; }
.steps div { border-left: .6mm solid var(--mark); padding-left: 3mm; }
.steps b { display:block; font-family:'Inter Display'; font-size: 10.5pt; }
.steps .n { font-family:'JetBrains Mono'; color: var(--mark); font-size: 8pt; }
.cta { margin-top: 10mm; background: var(--ink); color:#fff; border-radius: 2mm; padding: 7mm 8mm; }
.cta h3 { font-size: 15pt; margin-bottom: 2mm; }
.cta p { margin: 0; color: #d2dde3; }
.fine { position:absolute; left:16mm; right:16mm; bottom: 10mm; font-size: 7.5pt; color: var(--muted); border-top: .2mm solid var(--zinc2); padding-top: 2mm; display:flex; justify-content: space-between; }
"""


def catalogue_html(p: dict) -> str:
    builder = p["tier"] == 3
    why = WHY_BUILDER if builder else WHY_DEALER
    rows = []
    for code in p["models"]:
        name, axle, deck, atm, use = MODELS[code]
        rows.append(f"<tr><td class='code'>INX-{esc(code)}</td><td><div class='nm'>{esc(name)}</div>"
                    f"<div class='sub'>{esc(axle)} · {esc(deck)}</div></td><td class='atm'>{esc(atm)}</td>"
                    f"<td class='sub'>{esc(use)}</td></tr>")
    company = esc(p["company"])
    title = "Galvanised capacity, built to your drawings" if builder else "A better-built trailer range, landed for less"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Innovatix range for {company}</title>
<style>{CAT_CSS}</style></head><body>
<section class="page cover">
  <div class="top">
    <div class="brand">INNOVATIX<span>.</span></div>
    <h1>{esc(title)}</h1>
    <div class="for">Range proposal prepared for <b>{company}</b>, {esc(p['city'])}</div>
  </div>
  <div class="spangle">
    <div class="plate">
      <div class="hd">BUILD SPECIFICATION</div>
      <div class="row"><span>Finish</span><span>Hot-dip galvanised</span></div>
      <div class="row"><span>Steel</span><span>Mill-certified</span></div>
      <div class="row"><span>Welding</span><span>Certified welders</span></div>
      <div class="row"><span>Compliance</span><span>ADR · VIN plated</span></div>
      <div class="row"><span>Supply</span><span>Flat-pack · mixed loads</span></div>
    </div>
  </div>
</section>
<section class="page">
  <div class="eyebrow">Why Innovatix</div>
  <h2>{'A fabrication partner, not a competitor' if builder else 'Built in our own factory. Proven on paper.'}</h2>
  <div class="why">{''.join(f'<div><b>{esc(a)}</b>{esc(b)}</div>' for a, b in why)}</div>
  <div class="note"><b>See it before you commit.</b> We'll bring a weld cut-section and the mill certificates to our
  meeting, and can send a sample unit or a trial container so you can judge the quality and sell-through yourself.</div>
  <div class="eyebrow" style="margin-top:10mm">How it works</div>
  <div class="steps">{''.join(f'<div><span class="n">STEP {i}</span><b>{esc(a)}</b>{esc(b)}</div>' for i, (a, b) in enumerate(STEPS, 1))}</div>
  <div class="fine"><span>Innovatix · range proposal for {company}</span><span>Page 2</span></div>
</section>
<section class="page">
  <div class="eyebrow">Proposed range for {company}</div>
  <h2>Matched to the {esc(p['range_line'])} you already sell</h2>
  <table><thead><tr><th>Model</th><th>Description</th><th>ATM</th><th>Best for</th></tr></thead>
  <tbody>{''.join(rows)}</tbody></table>
  <div class="cta"><h3>Next step: a 30-minute meeting</h3>
  <p>We'll walk through this range, bring a weld sample and the mill certificates, and price your top models
  landed in {esc(p['city'])}. Reply to the email this came with to lock in a time.</p></div>
  <div class="fine"><span>Specifications are indicative. Final dimensions, ATM, componentry and dealer pricing are confirmed on quotation.
  Complete trailers are built to the Australian Design Rules and supplied with a VIN.</span><span>Page 3</span></div>
</section>
</body></html>"""


# ---- CRM CSV --------------------------------------------------------------------

def write_csv(prospects: list[dict]) -> None:
    cols = ["company", "segment", "state", "city", "website", "phone", "email", "contact_name", "source", "stage",
            "est_containers_per_month", "fit_score", "pain_points", "notes", "next_action", "next_action_date"]
    fit = {1: 8, 2: 6, 3: 4}
    with open(OUT / "qld_prospects.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in prospects:
            w.writerow({
                "company": p["company"], "segment": "trailer_manufacturer" if p["tier"] == 3 else "trailer_dealer",
                "state": "QLD", "city": p["city"], "website": p["website"], "phone": p["phones"][0],
                "email": p.get("email") or "", "contact_name": p.get("contact_name") or "",
                "source": f"QLD research {DATA['researched_on']}: {p['website']}", "stage": "researched",
                "est_containers_per_month": p["est_containers_pm"], "fit_score": fit[p["tier"]],
                "pain_points": p["sourcing"],
                "notes": f"Tier {p['tier']} ({p['priority']}). Angle: {p['angle']} | {p['cater']}",
                "next_action": "Send meeting email with range proposal, then call 2 days later",
                "next_action_date": "2026-11-26",
            })
        for c in DATA["call_only"]:
            w.writerow({"company": c["company"], "segment": "trailer_dealer", "state": "QLD", "phone": c["phone"],
                        "source": "Yellow Pages QLD, Nov 2026", "stage": "new", "fit_score": 5,
                        "notes": f"{c['address']}. {c.get('note', '')} Phone-qualify first.",
                        "next_action": "Qualifying call", "next_action_date": "2026-12-01"})


def main() -> None:
    (OUT / "catalogues").mkdir(parents=True, exist_ok=True)
    prospects = DATA["prospects"]
    emails = []
    for p in prospects:
        (OUT / "catalogues" / f"{p['id']}.html").write_text(catalogue_html(p), encoding="utf-8")
        emails.append(email_for(p))
    (OUT / "emails.json").write_text(json.dumps(emails, indent=1, ensure_ascii=False), encoding="utf-8")
    write_csv(prospects)
    pack = {"data": DATA, "emails": {e["id"]: e for e in emails},
            "models": {k: list(v) for k, v in MODELS.items()}}
    tpl = (HERE / "sales-pack.template.html").read_text(encoding="utf-8")
    (OUT / "sales-pack.html").write_text(
        tpl.replace("/*__PACK__*/null", json.dumps(pack, ensure_ascii=False).replace("</", "<\\/")), encoding="utf-8")
    print(f"Built {len(prospects)} catalogues, {len(emails)} emails, CSV and sales pack in {OUT}")


if __name__ == "__main__":
    main()
