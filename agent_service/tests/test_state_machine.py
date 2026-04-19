import pytest
from app.state_machine import FLOW, next_state


@pytest.mark.parametrize(
    ("mode", "current_state", "expected_state"),
    [
        (mode, current_state, expected_state)
        for mode, transitions in FLOW.items()
        for current_state, expected_state in transitions.items()
    ],
)
def test_next_state_matches_complete_transition_map(mode, current_state, expected_state):
    assert next_state(mode, current_state) == expected_state


def test_all_transition_targets_are_valid_states_in_the_same_mode():
    for mode, transitions in FLOW.items():
        valid_states = set(transitions)
        for current_state, next_state_name in transitions.items():
            assert next_state_name in valid_states, (
                f"{mode}.{current_state} -> {next_state_name} points outside the mode"
            )


def test_only_expected_terminal_self_loops_exist():
    terminal_self_loops = {
        mode: sorted(state for state, next_state_name in transitions.items() if state == next_state_name)
        for mode, transitions in FLOW.items()
    }

    assert terminal_self_loops == {
        "receive": ["refine_selected"],
        "build": ["rewrite_together"],
    }


def test_next_state_rejects_unsupported_mode():
    with pytest.raises(ValueError, match="Unsupported session mode"):
        next_state("unknown", "intake_problem")


def test_next_state_rejects_unsupported_current_state_for_valid_mode():
    with pytest.raises(ValueError, match="Unsupported state 'unknown_state' for mode 'receive'"):
        next_state("receive", "unknown_state")


def test_receive_mode_allows_semantic_continuation_after_present_choices():
    assert "optional_clarifier" not in FLOW["receive"]
    assert next_state("receive", "intake_problem") == "generate_candidates"
    assert next_state("receive", "generate_candidates") == "present_choices"
    assert next_state("receive", "present_choices") == "refine_selected"
    assert next_state("receive", "refine_selected") == "refine_selected"
