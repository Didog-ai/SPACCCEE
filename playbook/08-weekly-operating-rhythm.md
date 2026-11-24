# Weekly Operating Rhythm

One person can run this in about 15-20 hours of selling a week, with the bot doing the research, writing and record-keeping.

## Weekly targets

| Activity | Target / week |
|---|---|
| New prospects researched and added | 10-12 |
| Outreach touches (email + call + LinkedIn) | 25-30 |
| Real conversations | 6-8 |
| Meetings / site visits | 2-3 |
| Trial offers | 1 every 2 weeks |
| Existing-customer check-ins | every customer every 2 weeks |

## The week

**Monday (60 minutes)**
- `python -m sales_bot weekly`: review last week and plan this one
- `python -m sales_bot hunt <segment> <state>`: top up the pipeline
- Review and send the drafts (`python -m sales_bot drafts`)

**Tuesday-Thursday: selling days**
- Morning: `python -m sales_bot brief`, then calls in the 8-11am window (dealers are on site and less busy)
- Visits or travel
- After each call or visit, tell the bot in plain English what happened. It logs it and sets the next step.

**Friday (45 minutes)**
- Follow-ups and anything overdue (`python -m sales_bot followups`)
- Check existing customers' stock and reorders
- Post on LinkedIn

## Monthly

- Count containers ordered vs the target (bot: `pipeline`)
- Review conversion rates at each stage and update the assumptions in 01-strategy
- Check credit exposure against the limits (07-credit-and-risk)
- Plan next month's trip (region, and the 10+ meetings to book before travelling)

## Quarterly

- Business review with every active customer
- Decide which shows to walk or exhibit at next quarter
- Refresh the evidence pack (new photos, testimonials, case studies)
