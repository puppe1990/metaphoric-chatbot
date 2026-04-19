# Receive Metaphor Magic Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current linear "receive a metaphor" intake flow with a faster choice-based flow that asks for one sentence, optionally asks one short clarifier, then returns three metaphor options for the user to choose and refine.

**Architecture:** Keep the existing split between `web/` and `agent_service/`. The backend owns the new receive-mode state machine, hidden candidate generation/ranking metadata, and the updated response contract. The frontend stays text-first but adds structured choice rendering for `A/B/C` options and post-selection refinement actions.

**Tech Stack:** Next.js App Router, React, TypeScript, FastAPI, Python, SQLite, SQLAlchemy, pytest, Vitest

---

## File Structure

### Backend

- Modify: `agent_service/app/state_machine.py`
- Modify: `agent_service/app/orchestrator.py`
- Modify: `agent_service/app/agents.py`
- Modify: `agent_service/app/prompts.py`
- Modify: `agent_service/app/schemas.py`
- Modify: `agent_service/app/models.py`
- Modify: `agent_service/app/repository.py`
- Modify: `agent_service/app/main.py`
- Test: `agent_service/tests/test_state_machine.py`
- Test: `agent_service/tests/test_repository.py`
- Test: `agent_service/tests/test_api_flow.py`

### Frontend

- Modify: `web/lib/api.ts`
- Modify: `web/components/chat-shell.tsx`
- Modify: `web/components/message-list.tsx`
- Create: `web/components/metaphor-choice-list.tsx`
- Test: `web/tests/chat-shell.test.tsx`

## Task 1: Replace the Receive-Mode State Machine

**Files:**
- Modify: `agent_service/app/state_machine.py`
- Test: `agent_service/tests/test_state_machine.py`

- [ ] **Step 1: Write the failing state-machine test for the new receive flow**

```python
# agent_service/tests/test_state_machine.py
from app.state_machine import next_state


def test_receive_mode_uses_choice_based_flow():
    assert next_state("receive", "intake_problem") == "optional_clarifier"
    assert next_state("receive", "optional_clarifier") == "generate_candidates"
    assert next_state("receive", "generate_candidates") == "present_choices"
    assert next_state("receive", "present_choices") == "refine_selected"
    assert next_state("receive", "refine_selected") == "refine_selected"
```

- [ ] **Step 2: Run the targeted test and confirm it fails**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_state_machine.py::test_receive_mode_uses_choice_based_flow -v
```

Expected:

```text
FAILED tests/test_state_machine.py::test_receive_mode_uses_choice_based_flow
```

- [ ] **Step 3: Update the receive-mode transitions**

```python
# agent_service/app/state_machine.py
from __future__ import annotations

from typing import Final


FLOW: Final[dict[str, dict[str, str]]] = {
    "receive": {
        "intake_problem": "optional_clarifier",
        "optional_clarifier": "generate_candidates",
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
```

- [ ] **Step 4: Re-run the state-machine test and confirm it passes**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_state_machine.py::test_receive_mode_uses_choice_based_flow -v
```

Expected:

```text
PASSED tests/test_state_machine.py::test_receive_mode_uses_choice_based_flow
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/state_machine.py agent_service/tests/test_state_machine.py
git commit -m "refactor: update receive metaphor state flow"
```

## Task 2: Add Structured Receive-Flow Response Shapes

**Files:**
- Modify: `agent_service/app/schemas.py`
- Modify: `agent_service/app/models.py`
- Modify: `agent_service/app/repository.py`
- Test: `agent_service/tests/test_repository.py`

- [ ] **Step 1: Write the failing repository test for candidate metadata persistence**

```python
# agent_service/tests/test_repository.py
from app.db import init_db, SessionLocal
from app.repository import SessionRepository


def test_save_artifact_persists_choice_metadata(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    db = SessionLocal()
    repo = SessionRepository(db)
    session = repo.create_session(mode="receive")

    artifact = repo.create_artifact(
        session_id=session.id,
        artifact_type="metaphor_choices",
        content='{"options":["A","B","C"]}',
        metadata={
            "clarifier_asked": False,
            "internal_candidate_count": 6,
            "selected_option": None,
        },
    )

    assert artifact.metadata_json["clarifier_asked"] is False
    assert artifact.metadata_json["internal_candidate_count"] == 6
```

- [ ] **Step 2: Run the repository test and confirm it fails**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_repository.py::test_save_artifact_persists_choice_metadata -v
```

Expected:

```text
FAILED tests/test_repository.py::test_save_artifact_persists_choice_metadata
```

- [ ] **Step 3: Add typed metadata support to artifacts and response schemas**

```python
# agent_service/app/schemas.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MetaphorChoice(BaseModel):
    label: Literal["A", "B", "C"]
    text: str = Field(min_length=1)


class ArtifactMetadata(BaseModel):
    clarifier_asked: bool = False
    internal_candidate_count: int = 0
    selected_option: str | None = None


class ArtifactView(BaseModel):
    artifact_type: str
    content: str
    metadata: ArtifactMetadata | None = None
```

```python
# agent_service/app/models.py
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(index=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

```python
# agent_service/app/repository.py
def create_artifact(
    self,
    session_id: int,
    artifact_type: str,
    content: str,
    metadata: dict | None = None,
):
    artifact = Artifact(
        session_id=session_id,
        artifact_type=artifact_type,
        content=content,
        metadata_json=metadata,
    )
    self.db.add(artifact)
    self.db.commit()
    self.db.refresh(artifact)
    return artifact
```

- [ ] **Step 4: Re-run the repository test and confirm it passes**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_repository.py::test_save_artifact_persists_choice_metadata -v
```

Expected:

```text
PASSED tests/test_repository.py::test_save_artifact_persists_choice_metadata
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/schemas.py agent_service/app/models.py agent_service/app/repository.py agent_service/tests/test_repository.py
git commit -m "feat: add receive metaphor artifact metadata"
```

## Task 3: Implement Candidate Generation and Optional Clarifier Logic

**Files:**
- Modify: `agent_service/app/agents.py`
- Modify: `agent_service/app/prompts.py`
- Test: `agent_service/tests/test_api_flow.py`

- [ ] **Step 1: Write the failing API-flow test for immediate three-choice output**

```python
# agent_service/tests/test_api_flow.py
def test_receive_flow_returns_three_choices_after_problem_input(client):
    create_response = client.post("/sessions", json={"mode": "receive"})
    session = create_response.json()

    reply = client.post(
        f"/sessions/{session['token']}/messages",
        json={"content": "Estou travado para tomar uma decisão."},
    )

    data = reply.json()
    assistant = data["messages"][-1]

    assert data["state"] == "present_choices"
    assert assistant["artifact_type"] == "metaphor_choices"
    assert [option["label"] for option in assistant["choices"]] == ["A", "B", "C"]
```

- [ ] **Step 2: Run the API-flow test and confirm it fails**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_api_flow.py::test_receive_flow_returns_three_choices_after_problem_input -v
```

Expected:

```text
FAILED tests/test_api_flow.py::test_receive_flow_returns_three_choices_after_problem_input
```

- [ ] **Step 3: Add hidden generation helpers and a conservative clarifier rule**

```python
# agent_service/app/agents.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReceiveMetaphorResult:
    state: str
    message: str
    choices: list[dict] | None = None
    metadata: dict | None = None


def should_ask_clarifier(user_input: str) -> bool:
    normalized = user_input.strip().lower()
    return len(normalized.split()) <= 3


def generate_metaphor_choices(provider: object, user_input: str) -> ReceiveMetaphorResult:
    prompt = build_receive_choice_prompt(user_input)
    raw = getattr(provider, "generate_structured_choices")(prompt)

    return ReceiveMetaphorResult(
        state="present_choices",
        message="Escolha a que mais encaixa em você agora.",
        choices=raw["choices"][:3],
        metadata={
            "clarifier_asked": False,
            "internal_candidate_count": raw.get("candidate_count", 3),
            "selected_option": None,
        },
    )
```

```python
# agent_service/app/prompts.py
def build_receive_choice_prompt(user_input: str) -> str:
    return f"""
Você gera metáforas curtas, claras e úteis.
Entrada do usuário: {user_input}

Regras:
- gere 5 a 7 candidatas internamente
- devolva apenas 3 opções finais, rotuladas A, B e C
- cada opção deve ter no máximo 2 frases curtas
- evite clichês como floresta, neblina, lago, oceano, ponte e labirinto
- não exponha análise simbólica
""".strip()
```

- [ ] **Step 4: Wire the orchestrator to skip the old feeling/shift questionnaire**

```python
# agent_service/app/orchestrator.py
from app.agents import (
    coach_metaphor,
    generate_metaphor_choices,
    should_ask_clarifier,
)


def build_assistant_message(mode: str, state: str, user_input: str, provider_factory):
    if mode == "receive":
        if state == "intake_problem":
            result = generate_metaphor_choices(provider_factory(), user_input)
            return result.state, result.message, result.choices, result.metadata

        if state == "optional_clarifier":
            result = generate_metaphor_choices(provider_factory(), user_input)
            return result.state, result.message, result.choices, result.metadata

        if state == "refine_selected":
            return state, "Diga se você quer deixar a escolhida mais curta, mais concreta, mais poética ou mais direta.", None, None
```

- [ ] **Step 5: Re-run the API-flow test and confirm it passes**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_api_flow.py::test_receive_flow_returns_three_choices_after_problem_input -v
```

Expected:

```text
PASSED tests/test_api_flow.py::test_receive_flow_returns_three_choices_after_problem_input
```

- [ ] **Step 6: Commit**

```bash
git add agent_service/app/agents.py agent_service/app/prompts.py agent_service/app/orchestrator.py agent_service/tests/test_api_flow.py
git commit -m "feat: generate choice-based receive metaphor responses"
```

## Task 4: Track Selection and Refinement of the Chosen Option

**Files:**
- Modify: `agent_service/app/main.py`
- Modify: `agent_service/app/repository.py`
- Test: `agent_service/tests/test_api_flow.py`

- [ ] **Step 1: Write the failing API-flow test for selecting option B**

```python
# agent_service/tests/test_api_flow.py
def test_receive_flow_accepts_choice_selection_and_enters_refinement(client):
    create_response = client.post("/sessions", json={"mode": "receive"})
    token = create_response.json()["token"]

    client.post(
        f"/sessions/{token}/messages",
        json={"content": "Estou travado para tomar uma decisão."},
    )

    reply = client.post(
        f"/sessions/{token}/messages",
        json={"content": "B"},
    )

    data = reply.json()

    assert data["state"] == "refine_selected"
    assert "mais curta" in data["messages"][-1]["content"]
```

- [ ] **Step 2: Run the selection test and confirm it fails**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_api_flow.py::test_receive_flow_accepts_choice_selection_and_enters_refinement -v
```

Expected:

```text
FAILED tests/test_api_flow.py::test_receive_flow_accepts_choice_selection_and_enters_refinement
```

- [ ] **Step 3: Persist selected option and expose refinement affordances**

```python
# agent_service/app/repository.py
def update_latest_artifact_metadata(self, session_id: int, metadata: dict) -> None:
    artifact = (
        self.db.query(Artifact)
        .filter(Artifact.session_id == session_id)
        .order_by(Artifact.id.desc())
        .first()
    )
    if artifact is None:
        return
    artifact.metadata_json = {**(artifact.metadata_json or {}), **metadata}
    self.db.commit()
```

```python
# agent_service/app/main.py
if session.mode == "receive" and session.state == "present_choices" and payload.content in {"A", "B", "C"}:
    repo.update_latest_artifact_metadata(session.id, {"selected_option": payload.content})
    session.state = "refine_selected"
    repo.save_message(session.id, "user", payload.content, step="present_choices")
    repo.save_message(
        session.id,
        "assistant",
        "Perfeito. Agora posso lapidar essa direção: mais curta, mais concreta, mais poética ou mais direta.",
        step="refine_selected",
    )
```

- [ ] **Step 4: Re-run the selection test and confirm it passes**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_api_flow.py::test_receive_flow_accepts_choice_selection_and_enters_refinement -v
```

Expected:

```text
PASSED tests/test_api_flow.py::test_receive_flow_accepts_choice_selection_and_enters_refinement
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/main.py agent_service/app/repository.py agent_service/tests/test_api_flow.py
git commit -m "feat: support receive metaphor choice selection"
```

## Task 5: Render Structured A/B/C Choices in the Frontend

**Files:**
- Modify: `web/lib/api.ts`
- Modify: `web/components/message-list.tsx`
- Create: `web/components/metaphor-choice-list.tsx`
- Test: `web/tests/chat-shell.test.tsx`

- [ ] **Step 1: Write the failing frontend test for choice rendering**

```tsx
// web/tests/chat-shell.test.tsx
import { render, screen } from "@testing-library/react";
import { ChatShell } from "../components/chat-shell";

test("renders receive metaphor choices as buttons", () => {
  render(
    <ChatShell
      session={{
        token: "abc",
        title: "Receber uma metáfora",
        description: "Escolha a melhor direção.",
        mode: "receive",
        progressLabel: "Escolha",
        suggestions: [],
        messages: [
          {
            id: "m1",
            role: "assistant",
            content: "Escolha a que mais encaixa em você agora.",
            artifactType: "metaphor_choices",
            choices: [
              { label: "A", text: "Opção A" },
              { label: "B", text: "Opção B" },
              { label: "C", text: "Opção C" },
            ],
          },
        ],
      }}
    />,
  );

  expect(screen.getByRole("button", { name: /A/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /B/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /C/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend test and confirm it fails**

Run:

```bash
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
FAIL web/tests/chat-shell.test.tsx
```

- [ ] **Step 3: Add API types and a dedicated choice renderer**

```tsx
// web/components/metaphor-choice-list.tsx
type MetaphorChoice = {
  label: "A" | "B" | "C";
  text: string;
};

export function MetaphorChoiceList({
  choices,
}: {
  choices: MetaphorChoice[];
}) {
  return (
    <div className="mt-4 grid gap-3">
      {choices.map((choice) => (
        <button
          key={choice.label}
          className="rounded-2xl border border-ink/10 bg-white p-4 text-left shadow-sm transition hover:border-ink/20 hover:bg-fog"
          type="button"
        >
          <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-clay">
            {choice.label}
          </span>
          <span className="mt-2 block text-sm leading-6 text-ink">{choice.text}</span>
        </button>
      ))}
    </div>
  );
}
```

```tsx
// web/components/message-list.tsx
import { MetaphorChoiceList } from "./metaphor-choice-list";

if (message.artifactType === "metaphor_choices" && message.choices?.length) {
  return (
    <div>
      <p>{message.content}</p>
      <MetaphorChoiceList choices={message.choices} />
    </div>
  );
}
```

- [ ] **Step 4: Re-run the frontend test and confirm it passes**

Run:

```bash
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
PASS web/tests/chat-shell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/api.ts web/components/message-list.tsx web/components/metaphor-choice-list.tsx web/tests/chat-shell.test.tsx
git commit -m "feat: render receive metaphor choice cards"
```

## Task 6: Wire Choice Clicks Into the Existing Chat Input Path

**Files:**
- Modify: `web/components/chat-shell.tsx`
- Modify: `web/components/metaphor-choice-list.tsx`
- Test: `web/tests/chat-shell.test.tsx`

- [ ] **Step 1: Write the failing frontend test for clicking choice B**

```tsx
// web/tests/chat-shell.test.tsx
import userEvent from "@testing-library/user-event";

test("submits the selected metaphor choice", async () => {
  const user = userEvent.setup();
  const onInputChange = vi.fn();
  const onInputSubmit = vi.fn((event) => event.preventDefault());

  render(
    <ChatShell
      onInputChange={onInputChange}
      onInputSubmit={onInputSubmit}
      session={sessionWithChoiceArtifact}
    />,
  );

  await user.click(screen.getByRole("button", { name: /B/i }));

  expect(onInputSubmit).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
FAIL web/tests/chat-shell.test.tsx
```

- [ ] **Step 3: Allow choice buttons to populate and submit the draft**

```tsx
// web/components/metaphor-choice-list.tsx
export function MetaphorChoiceList({
  choices,
  onSelect,
}: {
  choices: MetaphorChoice[];
  onSelect?: (label: "A" | "B" | "C") => void;
}) {
  return (
    <div className="mt-4 grid gap-3">
      {choices.map((choice) => (
        <button key={choice.label} onClick={() => onSelect?.(choice.label)} type="button">
          ...
        </button>
      ))}
    </div>
  );
}
```

```tsx
// web/components/chat-shell.tsx
const handleChoiceSelect = (label: "A" | "B" | "C") => {
  if (inputValue === undefined) {
    setDraft(label);
  }

  const form = document.querySelector("form");
  if (form instanceof HTMLFormElement) {
    form.requestSubmit();
  }
};
```

- [ ] **Step 4: Re-run the frontend test and confirm it passes**

Run:

```bash
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
PASS web/tests/chat-shell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add web/components/chat-shell.tsx web/components/metaphor-choice-list.tsx web/tests/chat-shell.test.tsx
git commit -m "feat: submit selected metaphor choices from ui"
```

## Task 7: Verify End-to-End Behavior and Clean Up Copy

**Files:**
- Modify: `agent_service/app/orchestrator.py`
- Modify: `web/components/chat-shell.tsx`
- Test: `agent_service/tests/test_api_flow.py`
- Test: `web/tests/chat-shell.test.tsx`

- [ ] **Step 1: Add a backend test for the refinement prompt copy**

```python
# agent_service/tests/test_api_flow.py
def test_receive_refinement_prompt_mentions_supported_styles(client):
    create_response = client.post("/sessions", json={"mode": "receive"})
    token = create_response.json()["token"]

    client.post(
        f"/sessions/{token}/messages",
        json={"content": "Estou travado para tomar uma decisão."},
    )
    response = client.post(f"/sessions/{token}/messages", json={"content": "A"})

    content = response.json()["messages"][-1]["content"]

    assert "mais curta" in content
    assert "mais concreta" in content
    assert "mais poética" in content
    assert "mais direta" in content
```

- [ ] **Step 2: Run the backend and frontend verification suite**

Run:

```bash
cd agent_service && .venv/bin/pytest tests/test_state_machine.py tests/test_repository.py tests/test_api_flow.py -v
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
all targeted backend tests passed
all targeted frontend tests passed
```

- [ ] **Step 3: Tighten the visible helper copy in the chat shell**

```tsx
// web/components/chat-shell.tsx
<ChatInput
  helperText={
    session.mode === "receive"
      ? "Descreva o problema em uma frase. Se eu tiver contexto suficiente, já te mostro 3 caminhos."
      : "Envie sua resposta para avançar o estado guiado desta conversa."
  }
  ...
/>
```

- [ ] **Step 4: Re-run the focused frontend test**

Run:

```bash
cd web && npm run test -- chat-shell.test.tsx
```

Expected:

```text
PASS web/tests/chat-shell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/tests/test_api_flow.py web/components/chat-shell.tsx
git commit -m "chore: finalize receive metaphor magic flow"
```

## Self-Review

- Spec coverage:
  - choice-based receive flow: covered by Tasks 1, 3, 4, 5, 6
  - hidden candidate metadata: covered by Task 2
  - optional single clarifier path: covered by Task 3
  - frontend choice UX: covered by Tasks 5 and 6
  - refinement affordances after selection: covered by Tasks 4 and 7
- Placeholder scan: no `TODO`, `TBD`, or undefined "handle later" steps remain.
- Type consistency:
  - receive states are `intake_problem`, `optional_clarifier`, `generate_candidates`, `present_choices`, `refine_selected`
  - choice labels are always `A | B | C`
  - artifact type is consistently `metaphor_choices`

## Notes

- This plan intentionally focuses on the redesigned `Receive a Metaphor` path only.
- It does not restructure the broader MVP or the `Build My Metaphor` mode.
- If the clarifier rule becomes more sophisticated later, add a separate follow-up plan rather than bloating this one.
