# Build Coaching Tone Design

## Goal

Tighten the `build` mode coaching so the assistant behaves more like a metaphor coach and less like a corrective interviewer.

## Changes

- Keep the existing `build` state machine and API contract.
- Rewrite the coaching prompt to require:
  - one question per turn
  - short turns
  - using the user's latest image before suggesting alternatives
  - no explicit invalidation of the user's image
  - periodic provisional synthesis instead of endless questioning
  - movement from identity judgments toward process, mechanism, and scene
- Update the local fallback provider so development without a configured LLM still reflects the intended product behavior.
- Add a regression test for the fallback coaching style to lock in the new tone.

## Non-Goals

- No changes to the receive-mode flow.
- No database or schema changes.
- No frontend changes.

## Verification

- Run targeted backend tests covering build coaching behavior and the existing API flow.
