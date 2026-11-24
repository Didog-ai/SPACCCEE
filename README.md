# Innovatix Sales Manager Bot

An AI sales manager to take Innovatix from **4 to 10 containers a month** of Indian-made trailers sold into Australia.

It has two parts:

1. **The playbook** (`playbook/`): the sales strategy, funnel numbers, target segments, scripts, objection handling, shows, government tenders, credit-risk rules and the weekly routine. You can read it on its own.
2. **The bot** (`sales_bot/`): a Claude-powered sales manager with a built-in CRM. It researches prospects on the web, scores them, writes outreach, logs your calls and visits, chases follow-ups, and tracks you against the 10-container target.

The bot **never sends anything or contacts anyone**. Emails and messages are saved as drafts for you to review and send.

## Playbook

| File | What's in it |
|---|---|
| [00-company-facts](playbook/00-company-facts.md) | What's true about Innovatix, plus a **TO CONFIRM** list. Fill this in first. |
| [01-strategy](playbook/01-strategy.md) | The 4→10 maths, positioning, the Trial Container Program, the budget, the 90-day plan and the KPIs |
| [02-target-segments](playbook/02-target-segments.md) | Ideal customer scoring, the 9 segments, qualifying questions |
| [03-messaging-and-scripts](playbook/03-messaging-and-scripts.md) | Email sequence, call script, visit agenda, LinkedIn |
| [04-objection-handling](playbook/04-objection-handling.md) | Answers to the common pushbacks |
| [05-trade-shows-and-events](playbook/05-trade-shows-and-events.md) | Field days, caravan/boat/truck shows, associations, show checklist |
| [06-government-and-fleet](playbook/06-government-and-fleet.md) | Tender portals, council panels, how to win fleet buyers |
| [07-credit-and-risk](playbook/07-credit-and-risk.md) | Protecting pay-when-sold stock (PPSR, limits, warning signs) |
| [08-weekly-operating-rhythm](playbook/08-weekly-operating-rhythm.md) | Weekly targets and the routine |

## Setup (once)

You need Python 3.10+ and a Claude API key from https://console.anthropic.com.

```bash
pip install -r requirements.txt
```

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Load your current customers. Copy `data/prospects_template.csv`, fill in one row per wholesaler with `stage` set to `active` and their real containers per month, then:

```bash
python -m sales_bot import my_customers.csv
```

## Daily use

```bash
python -m sales_bot brief
```
Today's priorities: who to call, and why.

```bash
python -m sales_bot chat
```
Talk to it like a sales manager. For example:
- *"Find 10 trailer dealers in regional NSW and add them."*
- *"Just visited Smith Trailers in Dubbo. Spoke to Mark, the owner. Unhappy with rust on his current cages, sells about 15 a month. Wants pricing on 7x4 and 8x5 cages. I said I'd send it Thursday."*
- *"Write the first email to prospect 12."*
- *"Prep me for my meeting with Coastal Hire tomorrow."*
- *"Plan a 4-day Perth trip in February."*
- *"Which councils in QLD are tendering for trailers right now?"*

```bash
python -m sales_bot hunt trailer_dealer WA
```
Researches and adds about 10 new prospects. Segments: `trailer_dealer`, `trailer_manufacturer`, `hire_company`, `rural_ag`, `caravan_camper_boat`, `fleet_buyer`, `government`, `auto_accessory`, `online_reseller`.

```bash
python -m sales_bot weekly
```
Weekly review against the 10-container target.

```bash
python -m sales_bot drafts
```
Read the drafted emails. Mark one as sent with `--sent ID`.

These commands don't use the AI and are free:

```bash
python -m sales_bot pipeline
```

```bash
python -m sales_bot followups
```

```bash
python -m sales_bot export backup.csv
```

## How the CRM works

Everything is stored in `data/crm.db` (a single file on your computer, not committed to git). Back it up regularly with `export`.

Pipeline stages: `new → researched → contacted → engaged → meeting → trial_offered → trial_order → active`, plus `nurture`, `lost` and `not_a_fit`. The forecast weights each prospect's estimated containers/month by its stage probability (see `sales_bot/db.py`).

## Settings (environment variables)

| Variable | Default | |
|---|---|---|
| `INNOVATIX_TARGET_CONTAINERS` | 10 | Monthly target |
| `INNOVATIX_BASELINE_CONTAINERS` | 4 | Current volume |
| `INNOVATIX_MODEL` | claude-opus-5-5 | Claude model |
| `INNOVATIX_EFFORT` | medium | `low` is cheaper/faster; `high` is more thorough research |
| `INNOVATIX_DB` | data/crm.db | CRM file location |

## Cost

Typical use (a daily brief, a few chats and one or two prospect hunts a week) costs roughly A$50-150 a month in API fees. Web research is the most expensive part. Check actual spend in the Anthropic console.
