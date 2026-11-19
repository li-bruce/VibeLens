"""Route model-construction work without changing the decision store or intent.

The coding agent supplies source-backed models and pending interpretations.
Deterministic checks derive missing work from these obligations, independently of
whether the agent has written a question. This module does not infer requirements
from natural language or generate user answers.
"""

from copy import deepcopy

from ..concepts.decision_contract import condition_state, has_unanswered_prompt


def present_question(decision, preference, *, locale=None):
    """Select authored wording without editing intent, history or participation.

    Review commands may override the display language for this presentation.
    Missing localized wording retains the recorded question, never an invented
    translation or answer.
    """
    item = deepcopy(decision)
    locale = locale or preference.get("language", "en")
    depth = preference.get("explanation_depth", "outcome")
    wording = decision.get("routing", {}).get("wording", {}).get(locale, {})
    item["question"] = wording.get(
        "technical" if depth == "technical" else "business", item["question"]
    )
    item.pop("technical_detail", None)
    if depth == "mixed" and wording.get("technical"):
        item["technical_detail"] = wording["technical"]
    item["language"] = locale
    item["explanation_depth"] = depth
    return item


def route(document, decisions, active):
    """Return small human rounds and the complete agent/checker work queues."""
    preference = document.get("participation", {})
    human, agent, checker, waiting, inactive = [], [], [], [], []
    for identity in sorted(
        active,
        key=lambda key: (not decisions[key]["blocking"], decisions[key].get("priority", 2), key),
    ):
        decision = decisions[identity]
        routing = decision.get("routing")
        condition = condition_state(decision, decisions)
        if condition == "inactive":
            inactive.append(identity)
            continue
        if decision["status"] == "resolved":
            continue
        if routing is None:
            agent.append(
                {"id": identity, "task": "classify_decision", "affects": decision["affects"]}
            )
            # Migration keeps the former human question behavior until an
            # explicit classification exists. Never silently hide its prompt.
            if (
                decision["status"] == "open"
                and not has_unanswered_prompt(decision)
                and all(
                    decisions[key]["status"] == "resolved" for key in decision.get("depends_on", [])
                )
            ):
                human.append(deepcopy(decision))
            continue
        if condition == "waiting" or any(
            decisions[key]["status"] != "resolved" for key in decision.get("depends_on", [])
        ):
            waiting.append(identity)
            continue
        item = present_question(decision, preference)
        if routing["owner"] == "human":
            if decision["status"] in {
                "open",
                "partial",
                "contradicted",
            } and not has_unanswered_prompt(decision):
                human.append(item)
            else:
                waiting.append(identity)
        elif routing["owner"] == "agent":
            agent.append(item)
        else:
            checker.append(item)
    return {
        "questions": human[:3],
        "remaining_human": [d["id"] for d in human[3:]],
        "agent_work": agent,
        "checker_work": checker,
        "waiting": waiting,
        "inactive": inactive,
        "preference": deepcopy(preference),
        "evidence_validation": "not_checked",
    }
