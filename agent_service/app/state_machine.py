from __future__ import annotations

from typing import Final


FLOW: Final[dict[str, dict[str, str]]] = {
    "receive": {
        "intake_problem": "generate_candidates",
        "generate_candidates": "present_choices",
        "present_choices": "refine_selected",
        "refine_selected": "refine_selected",
    },
    "build": {
        "intake_problem": "identify_core_conflict",
        "identify_core_conflict": "offer_symbolic_fields",
        "offer_symbolic_fields": "user_selects_symbol",
        "user_selects_symbol": "user_attempt",
        "user_attempt": "coach_feedback",
        "coach_feedback": "rewrite_together",
        "rewrite_together": "rewrite_together",
    },
}


def next_state(mode: str, current_state: str) -> str:
    try:
        mode_flow = FLOW[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported session mode: {mode!r}") from exc

    try:
        return mode_flow[current_state]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported state {current_state!r} for mode {mode!r}"
        ) from exc
