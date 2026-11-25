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
ASSETS = "../assets"  # print-sized product photos (made by web_assets()), relative to out/catalogues/
DATA = json.loads((HERE / "prospects.json").read_text(encoding="utf-8"))

# Indicative Pinnacle Trailers range. Final spec, ATM and pricing are confirmed on quote.
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
    "LM85":  ("8x5 Lawn Mowing / Gardening Trailer", "Single axle", "Enclosed mower box with gas-strut side door, fold-down side ramp, rear barn doors, twin loading ramps", "to suit", "Mowing contractors and landscapers."),
    "GB":    ("Golf Buggy Trailer", "Single axle", "Tilt deck, fold-down checker-plate rear ramp, checker-plate guards", "750 kg", "Golf buggies, ride-on mowers and small vehicles."),
    "ATV85": ("8x5 ATV / Mower Trailer", "Single axle", "Full-width fold-down ramp, tilt body", "750 kg (1400 kg braked option)", "Mowers, quads and side-by-sides."),
    "VAN74": ("7x4 Enclosed Van Trailer", "Single axle", "Lockable, rear barn doors", "750 kg", "Secure storage for trades and events."),
    "BT55":  ("Galvanised Boat Trailer", "Single or tandem axle", "Multi-roller, boats to 5.5 m", "750-1400 kg", "Salt-water ready."),
    "OR75":  ("7x5 Off-Road Box", "Single axle, braked", "Heavy-duty springs, off-road coupling", "1400 kg", "Built for outback tracks."),
    "LS85":  ("8x5 Stock Crate Trailer", "Tandem axle, braked", "Galvanised crate, rear ramp", "2000 kg", "Small livestock and farm moves."),
    "UT":    ("Steel Ute Tray", "Single or dual cab", "Checker-plate floor, drop sides, headboard with ladder rack", "n/a", "Sell trays alongside trailers to the same trade buyers."),
    "CHS":   ("Rolling Chassis / Flat-Pack Kit", "Any size 6x4 to 12x6", "Galvanised chassis, drawbar and axle mounts, built to your drawings", "to suit", "Finish and badge them in your own workshop."),
    "CAGE":  ("Cages and Sub-Assemblies", "Made to order", "Mesh cages, drawbars, ramps, tailgates", "n/a", "Extra fabrication capacity."),
}

WHY_DEALER = [
    ("Certified steel", "Mill certificates and welder certifications supplied, so you can check the steel and the welds yourself."),
    ("Galvanised or painted", "Hot-dip galvanised for coastal and heavy use, or a tough painted finish for golf buggy and specialty trailers."),
    ("ADR and CTA approved", "ADR-approved drawbars for trailers up to 3500 kg and CTA-approved couplings up to 3500 kg. VINs supplied if you need them."),
    ("Factory-direct price", "Our own factory, no trader in between. Landed below comparable imports."),
    ("Pay as you sell", "Flexible credit terms: you can pay for trailers as they sell."),
    ("Mix any container", "Different trailers in one container, plus extra parts if you build or repair locally."),
    ("Our designs, or yours", "Choose from our own proven designs, or make yours unique with custom features, depending on volume."),
    ("Low-risk start", "Start with a trial container, or a sample unit to inspect first."),
]
WHY_BUILDER = [
    ("Extra capacity", "Galvanised chassis, sub-assemblies or standard sizes built to your drawings."),
    ("Certified steel", "Mill certificates and welder certifications supplied with every batch."),
    ("Your brand stays yours", "Supplied unbranded or under a separate value brand, so your own line is untouched."),
    ("ADR and CTA approved", "ADR-approved drawbars and CTA-approved couplings for trailers up to 3500 kg. VINs supplied if needed."),
    ("Parts in any container", "Mix complete trailers with drawbars, couplings, chassis and spare parts for your workshop."),
    ("Flexible terms", "Flexible credit terms, and custom features to suit your designs based on volume."),
]
STEPS = [
    ("Choose your mix", "Mix any trailers in one container and add extra parts. Custom features available based on volume."),
    ("We build and ship", "Built and finished in our factory, flat-packed to fit more trailers per container."),
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
            "ADR-approved drawbars and CTA-approved couplings for trailers up to 3500 kg, with VINs supplied if needed",
            "Mixed containers: complete trailers plus extra parts and components for your workshop",
            "Supplied unbranded or under a separate brand, so your Australian-made line stays separate",
            "Custom features to suit your designs, depending on volume, and flexible credit terms",
        ]
        lead = "Here's what we can offer a builder like you:"
        intro = ("I'm with Pinnacle Trailers. We're a steel fabrication company with our own factory in India, "
                 "and we supply galvanised trailers and components to Queensland trailer businesses.")
    else:
        subject = f"Galvanised trailer supply for {p['company'].split(' (')[0]}: 30-minute meeting?"
        intro = ("I'm with Pinnacle Trailers. We're a steel fabrication company with our own factory in India, and we build "
                 "galvanised and painted trailers that ship flat-packed to Australian dealers. Several Queensland "
                 "dealers already stock our range, and the response has been very strong.")
        if p["id"] in ("wide-bay", "toowoomba-trailers"):
            lead = "Here's why dealers are moving their imported range to us:"
        elif p["tier"] == 1:
            lead = "If some of your range comes from Chinese suppliers, here's why dealers are moving that volume to us:"
        else:
            lead = "Here's why dealers are adding us as a second supplier:"
        bullets = [
            "Higher-grade, certified steel: we supply mill certificates and welder certifications so you can check it yourself",
            "Hot-dip galvanised or tough painted finishes",
            "ADR-approved drawbars and CTA-approved couplings for trailers up to 3500 kg, with VINs supplied if you need them",
            "Factory-direct pricing, landed below comparable Chinese imports",
            "Flexible credit terms: you can pay as the trailers sell",
            "Mixed containers: different trailers in one load, plus extra parts if you build or repair locally",
            "A trial container or sample unit, so you can test us without the risk",
            "Dependable lead times straight from our own factory, with no trader in the middle",
            "Our own proven designs, or custom features to make yours unique, depending on volume",
        ]
    body = "\n".join([
        greet, "",
        p["opener"], "",
        intro, "",
        lead,
        *[f"- {b}" for b in bullets], "",
        f"I've attached a short range proposal built around the {p['range_line']} you already sell, with photos of recent builds from our factory.", "",
        f"Could we find 30 minutes in the next couple of weeks? I'm happy to meet {p['meeting']} and bring a weld "
        "cut-section and our mill certificates so you can see the build quality first-hand. Would Tuesday 1 or "
        "Thursday 3 December work, or is there a better time for you?", "",
        "Kind regards,",
    ])
    html_body = (
        f"<p>{esc(greet)}</p><p>{esc(p['opener'])}</p><p>{esc(intro)}</p><p>{esc(lead)}</p><ul>"
        + "".join(f"<li>{esc(b)}</li>" for b in bullets)
        + f"</ul><p>I've attached a short range proposal built around the {esc(p['range_line'])} you already sell, with photos of recent builds from our factory.</p>"
        f"<p>Could we find 30 minutes in the next couple of weeks? I'm happy to meet {esc(p['meeting'])} and bring a "
        "weld cut-section and our mill certificates so you can see the build quality first-hand. Would Tuesday 1 or "
        "Thursday 3 December work, or is there a better time for you?</p><p>Kind regards,</p>"
    )
    return {"id": p["id"], "to": p.get("email"), "subject": subject, "body": body, "html": html_body,
            "attachment": f"Pinnacle-Trailers-Range-{p['id']}.pdf"}


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
.logo { height: 20mm; width: auto; display: block; }
.cover h1 { font-size: 34pt; line-height: 1.05; font-weight: 800; margin-top: 46mm; max-width: 150mm; }
.cover .for { margin-top: 8mm; font-size: 13pt; color: #c5d3dc; }
.cover .for b { color:#fff; }
.cover h1 { margin-top: 14mm; }
.spangle { margin-top: auto; height: 112mm; background-size: cover; background-position: center 72%; position: relative; }
.spangle::after { content: "Galvanised 8x5 lawn mowing trailer, built in our factory"; position: absolute; right: 16mm; bottom: 6mm;
  font-family: 'JetBrains Mono'; font-size: 7.5pt; color: #fff; background: rgba(22,35,45,.72); padding: 1mm 2mm; border-radius: 1mm; }
.proof { display: grid; grid-template-columns: repeat(6, 1fr); gap: 4mm 3mm; }
.proof figure { margin: 0; }
.proof img { width: 100%; display: block; object-fit: cover; border-radius: 1mm; }
.proof .big img { height: 100mm; }
.proof .sm img { height: 62mm; }
.proof .big { grid-column: span 4; } .proof .side { grid-column: span 2; } .proof .side img { height: 100mm; }
.proof .sm { grid-column: span 2; }
.proof .full { grid-column: span 6; } .proof .full img { height: 72mm; }
.proof .g img { height: 64mm; }
.proof .half { grid-column: span 3; } .proof .half img { height: 70mm; }
.proof figcaption { font-size: 8pt; color: var(--muted); margin-top: 1.5mm; line-height: 1.35; }
.proof figcaption b { color: var(--ink); font-weight: 600; }
.lede2 { color: var(--muted); max-width: 150mm; margin: -3mm 0 6mm; }
.plate { margin-top: 7mm; background: #f4f6f7; color: var(--ink); border-radius: 2mm;
  padding: 5mm 6mm; width: 92mm; }
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
        rows.append(f"<tr><td class='code'>PT-{esc(code)}</td><td><div class='nm'>{esc(name)}</div>"
                    f"<div class='sub'>{esc(axle)} · {esc(deck)}</div></td><td class='atm'>{esc(atm)}</td>"
                    f"<td class='sub'>{esc(use)}</td></tr>")
    company = esc(p["company"])
    title = "Galvanised capacity, built to your drawings" if builder else "A better-built trailer range, landed for less"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Pinnacle Trailers range for {company}</title>
<style>{CAT_CSS}</style></head><body>
<section class="page cover">
  <div class="top">
    <img class="logo" src="{ASSETS}/pinnacle-logo-white.png" alt="Pinnacle Trailers">
    <h1>{esc(title)}</h1>
    <div class="for">Range proposal prepared for <b>{company}</b>, {esc(p['city'])}</div>
    <div class="plate">
      <div class="hd">BUILD SPECIFICATION</div>
      <div class="row"><span>Finish</span><span>Galvanised or painted</span></div>
      <div class="row"><span>Steel</span><span>Mill-certified</span></div>
      <div class="row"><span>Welding</span><span>Certified welders</span></div>
      <div class="row"><span>Drawbars</span><span>ADR approved · to 3500 kg</span></div>
      <div class="row"><span>Couplings</span><span>CTA approved · to 3500 kg</span></div>
      <div class="row"><span>VIN</span><span>Supplied if needed</span></div>
      <div class="row"><span>Supply</span><span>Mixed loads · extra parts</span></div>
    </div>
  </div>
  <div class="spangle" style="background-image:url('{ASSETS}/enclosed-trailer-side-door-ramp.jpg')">
  </div>
</section>
<section class="page">
  <div class="eyebrow">Why Pinnacle Trailers</div>
  <h2>{'A fabrication partner, not a competitor' if builder else 'Built in our own factory. Proven on paper.'}</h2>
  <div class="why">{''.join(f'<div><b>{esc(a)}</b>{esc(b)}</div>' for a, b in why)}</div>
  <div class="note"><b>See it before you commit.</b> We'll bring a weld cut-section and the mill certificates to our
  meeting, and can send a sample unit or a trial container so you can judge the quality and sell-through yourself.</div>
  <div class="eyebrow" style="margin-top:10mm">How it works</div>
  <div class="steps">{''.join(f'<div><span class="n">STEP {i}</span><b>{esc(a)}</b>{esc(b)}</div>' for i, (a, b) in enumerate(STEPS, 1))}</div>
  <div class="fine"><span>Pinnacle Trailers · range proposal for {company}</span><span>Page 2</span></div>
</section>
<section class="page">
  <div class="eyebrow">Proof of work · galvanised trailers</div>
  <h2>Built in our factory. Already working for Australian dealers.</h2>
  <p class="lede2">Recent builds photographed at our factory before dispatch, from the same production line that
  supplies our Queensland and Victorian dealers. Every panel, frame and drawbar is hot-dip galvanised.</p>
  <div class="proof">
    <figure class="big"><img src="{ASSETS}/enclosed-trailer-side-door-ramp.jpg" alt="Galvanised enclosed trailer, three-quarter view with side door and ramp open">
      <figcaption><b>8x5 lawn mowing / gardening trailer.</b> Fully galvanised, enclosed mower box with gas-strut side door and fold-down checker-plate side ramp, A-frame drawbar.</figcaption></figure>
    <figure class="side"><img src="{ASSETS}/enclosed-trailer-loading-ramps.jpg" alt="Galvanised trailer with twin loading ramps">
      <figcaption><b>Twin loading ramps.</b> Checker-plate ramps for mowers, quads and equipment.</figcaption></figure>
    <figure class="sm"><img src="{ASSETS}/enclosed-trailer-rear-doors-open.jpg" alt="Galvanised trailer with rear barn doors open">
      <figcaption><b>Barn doors open.</b> Checker-plate floor and doors, internal rails, ramp stowage underneath.</figcaption></figure>
    <figure class="sm"><img src="{ASSETS}/enclosed-trailer-front-drawbar.jpg" alt="Galvanised trailer front view showing A-frame drawbar">
      <figcaption><b>Front view.</b> Galvanised A-frame drawbar, lockable front door with T-handle.</figcaption></figure>
    <figure class="sm"><img src="{ASSETS}/galvanised-highside-trailer.jpg" alt="Galvanised high-side trailer, rear view with doors closed">
      <figcaption><b>Closed up.</b> Lockable twin barn doors and LED combination lamps.</figcaption></figure>
  </div>
  <div class="fine"><span>Pinnacle Trailers · range proposal for {company}</span><span>Page 3</span></div>
</section>
<section class="page">
  <div class="eyebrow">Proof of work · golf buggy trailers</div>
  <h2>Golf buggy trailers, ready for the course.</h2>
  <p class="lede2">Tilt-deck golf buggy trailers with a full-width fold-down ramp, checker-plate guards and a tough painted finish.
  Built in our factory and supplied to Australian dealers.</p>
  <div class="proof">
    <figure class="full"><img src="{ASSETS}/golf-buggy-trailer-side.jpg" alt="Golf buggy trailer side view">
      <figcaption><b>Golf buggy trailer.</b> Single axle, tilt deck, checker-plate guards, jockey wheel and safety chains.</figcaption></figure>
    <figure class="sm g"><img src="{ASSETS}/golf-buggy-trailer-rear-3q.jpg" alt="Golf buggy trailer from the rear">
      <figcaption><b>Rear view.</b> Checker-plate deck and tailgate ramp, LED combination lamps, rear stand wheels.</figcaption></figure>
    <figure class="sm g"><img src="{ASSETS}/golf-buggy-trailer-ramp-down.jpg" alt="Golf buggy trailer with ramp lowered" style="object-position: 40% 50%">
      <figcaption><b>Ramp down.</b> Full-width ramp for driving the buggy straight on.</figcaption></figure>
    <figure class="sm g"><img src="{ASSETS}/golf-buggy-trailer-tilt-front.jpg" alt="Golf buggy trailer with deck tilted" style="object-position: 62% 50%">
      <figcaption><b>Tilt deck.</b> Body tilts for easy loading without a winch.</figcaption></figure>
  </div>
  <div class="fine"><span>Pinnacle Trailers · range proposal for {company}</span><span>Page 4</span></div>
</section>
<section class="page">
  <div class="eyebrow">Proof of work · steel ute trays</div>
  <h2>Alongside trailers, we build heavy-duty ute trays.</h2>
  <p class="lede2">Sell trays to the same trade buyers who buy your trailers. Same factory, same steel, same quality checks.</p>
  <div class="proof">
    <figure class="big"><img src="{ASSETS}/ute-tray-dropsides-open.jpg" alt="Steel ute tray with drop sides lowered">
      <figcaption><b>Steel ute tray.</b> Drop sides with over-centre latches, checker-plate floor, headboard with ladder rack.</figcaption></figure>
    <figure class="side"><img src="{ASSETS}/ute-tray-dropsides-headboard.jpg" alt="Steel ute tray with sides up">
      <figcaption><b>Sides up.</b> Full-height sides and integrated under-tray frame.</figcaption></figure>
    <figure class="half"><img src="{ASSETS}/ute-tray-flatdeck-rear.jpg" alt="Flat-deck tray from the rear">
      <figcaption><b>Flat deck, rear.</b> Tailgate with tie rail and side load posts.</figcaption></figure>
    <figure class="half"><img src="{ASSETS}/ute-tray-flatdeck.jpg" alt="Flat-deck tray ready for dispatch">
      <figcaption><b>Flat deck.</b> Checker-plate floor, finished and ready to ship.</figcaption></figure>
  </div>
  <div class="fine"><span>Pinnacle Trailers · range proposal for {company}</span><span>Page 5</span></div>
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
  Drawbars are ADR approved and couplings CTA approved for trailers up to 3500 kg ATM. VINs supplied on request.</span><span>Page 6</span></div>
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


def web_assets() -> None:
    """Copy photos into out/assets, resized for print so each PDF stays email-friendly."""
    from PIL import Image
    dst = OUT / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    for src in (HERE / "assets").iterdir():
        im = Image.open(src)
        if src.suffix.lower() == ".png":
            im.save(dst / src.name)
            continue
        im.thumbnail((1000, 1000))
        im.convert("RGB").save(dst / src.name, quality=72, optimize=True)


def main() -> None:
    web_assets()
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
