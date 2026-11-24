# QLD Dealer Prospecting (November 2026)

19 researched Queensland trailer businesses, plus a call-only list of 15 and a list of businesses not worth approaching.

| File | What it is |
|---|---|
| `prospects.json` | Source data: contact details, evidence quoted from each website, sourcing, pitch angle and proposed models |
| `out/catalogues/Innovatix-Range-<dealer>.pdf` | Dealer-facing range proposal for each prospect |
| `out/emails.json` | Meeting-request email for each prospect |
| `out/qld_prospects.csv` | CRM import (`python -m sales_bot import research/qld/out/qld_prospects.csv`) |
| `out/sales-pack.html` | Internal sales pack page (published as a private artifact) |

## Tiers

1. **Importers / value galvanised resellers.** Open with the angle that we're a better alternative to Chinese supply.
2. **Dealers whose sourcing isn't stated.** Position us as a second supplier.
3. **Australian builders.** Offer capacity, chassis or a private-label partnership. Never use the China angle.

## Rebuild after editing `prospects.json`

```bash
python3 research/qld/build.py
```

```bash
node research/qld/render_pdfs.mjs
```

Model specs in `build.py` (`MODELS`) are indicative. Replace them with Innovatix's real range and specs before wide use.
