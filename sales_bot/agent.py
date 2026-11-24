"""The Innovatix sales-manager agent: a Claude tool-use loop over the local CRM plus web research."""
from __future__ import annotations

import json
from datetime import date

import anthropic

from .config import BASELINE_CONTAINERS, EFFORT, MODEL, PLAYBOOK_DIR, TARGET_CONTAINERS
from .tools import ALL_TOOLS

WEB_TOOLS = [
    {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 8,
        "user_location": {"type": "approximate", "country": "AU", "timezone": "Australia/Brisbane"},
    },
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8},
]

ROLE = f"""You are the sales manager for Innovatix, a steel fabrication business with its own factory in India \
that manufactures trailers and exports them flat-packed in shipping containers to Australia.

Your mission: grow sales from about {BASELINE_CONTAINERS:g} containers a month to {TARGET_CONTAINERS:g}, \
by winning new Australian buyers (trailer dealers and wholesalers first, then manufacturers, hire fleets, \
rural/ag, caravan/camper/boat dealers, fleet buyers and government) and growing existing accounts.

You work with the owner, who is the only salesperson: they visit dealers, make calls and attend shows. \
Your job is to make every hour they spend selling count:
- Find and research prospects (use web search), qualify them against the ideal customer profile, and add them \
to the CRM with a fit score, an honest estimate of containers/month, and a next action.
- Tell the owner who to contact next and why, and prepare them: talking points, likely objections, questions to ask.
- Write outreach (emails, LinkedIn messages, call scripts, follow-ups) tailored to the prospect, and save it \
with save_draft. You never send anything yourself.
- Keep the CRM accurate: log every activity the owner reports, move stages, set next actions with dates.
- Track the numbers against the target and say plainly when activity or pipeline is too low to hit it.

How you work:
- Be direct and practical, like a seasoned B2B sales manager. Lead with the recommendation, then the reasoning.
- Give specific actions with names, dates and numbers, not generic advice.
- Never invent facts about prospects (names, phone numbers, emails, volumes). If you didn't find it in a \
source or get it from the owner, say it's unknown. Cite the URL you got it from in the prospect's source field.
- Never invent facts about Innovatix either (prices, lead times, certifications, specs). The company facts \
below list what's confirmed; anything marked TO CONFIRM must be asked of the owner, not assumed.
- Don't disparage named competitors. Compare against "typical imported trailers" and back claims with \
Innovatix's own evidence (mill certificates, welder certs, galvanising specs, photos, testimonials).
- Before a write that changes a record's stage to lost/not_a_fit, or records an order, make sure the owner \
actually told you that happened.
- Before searching the web for new prospects, check the CRM with find_prospects so you don't add duplicates.
- Use read_playbook for detailed scripts, segment lists, show calendars, government tender portals, credit \
risk rules and the weekly rhythm.
"""


def _system_prompt() -> list[dict]:
    facts = (PLAYBOOK_DIR / "00-company-facts.md").read_text(encoding="utf-8")
    strategy = (PLAYBOOK_DIR / "01-strategy.md").read_text(encoding="utf-8")
    text = f"{ROLE}\n\n<company_facts>\n{facts}\n</company_facts>\n\n<strategy>\n{strategy}\n</strategy>"
    return [{"type": "text", "text": text}]


class SalesAgent:
    def __init__(self, client: anthropic.Anthropic | None = None, verbose: bool = True):
        self.client = client or anthropic.Anthropic()
        self.tools = {t.name: t for t in ALL_TOOLS}
        self.tool_defs = [t.to_dict() for t in ALL_TOOLS] + WEB_TOOLS
        self.system = _system_prompt()
        self.messages: list = []
        self.verbose = verbose
        self._dated = False

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  \033[2m{msg}\033[0m", flush=True)

    def _run_tool(self, block) -> dict:
        tool = self.tools.get(block.name)
        if tool is None:
            return {"type": "tool_result", "tool_use_id": block.id, "content": f"Unknown tool {block.name}",
                    "is_error": True}
        try:
            out = tool.call(block.input)
            return {"type": "tool_result", "tool_use_id": block.id, "content": str(out)}
        except Exception as e:  # tool errors go back to the model so it can correct itself
            return {"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True}

    def ask(self, text: str, max_steps: int = 40) -> str:
        if not self._dated:
            text = f"(Today is {date.today().isoformat()}.)\n\n{text}"
            self._dated = True
        self.messages.append({"role": "user", "content": text})

        for _ in range(max_steps):
            response = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=self.system,
                tools=self.tool_defs,
                messages=self.messages,
                thinking={"type": "adaptive"},
                output_config={"effort": EFFORT},
                cache_control={"type": "ephemeral"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            self.messages.append({"role": "assistant", "content": response.content})

            for b in response.content:
                if b.type == "server_tool_use":
                    q = b.input.get("query") or b.input.get("url") or ""
                    self._log(f"[{b.name}] {q}")

            if response.stop_reason == "pause_turn":
                continue
            if response.stop_reason == "tool_use":
                results = []
                for b in response.content:
                    if b.type == "tool_use":
                        self._log(f"[{b.name}] {json.dumps(b.input, ensure_ascii=False)[:160]}")
                        results.append(self._run_tool(b))
                self.messages.append({"role": "user", "content": results})
                continue

            reply = "\n".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason == "refusal":
                reply += "\n\n[The model declined part of this request. Try rephrasing.]"
            elif response.stop_reason == "max_tokens":
                reply += "\n\n[Reply was cut off at the length limit. Ask me to continue.]"
            return reply

        return "[Stopped after too many steps in one turn. Ask me to continue.]"
