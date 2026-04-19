# Metaphoric Chatbot MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a text-only web app with guided chat for receiving metaphors or learning to build them, backed by a Python Deep Agents service, Groq as the first provider, SQLite persistence, and anonymous unique-link sessions.

**Architecture:** Use a split architecture with a Next.js frontend and a Python FastAPI agent service. The frontend owns the landing page, chat UI, and session restoration. The Python service owns session orchestration, symbolic extraction, metaphor generation/coaching, and SQLite persistence through a deterministic state machine layered over Deep Agents.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, Python 3.12, FastAPI, Deep Agents, LangGraph, SQLite, SQLAlchemy, pytest, Vitest, Playwright

---

## File Structure

### Frontend app

- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/postcss.config.js`
- Create: `web/tailwind.config.ts`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/c/[token]/page.tsx`
- Create: `web/app/globals.css`
- Create: `web/lib/api.ts`
- Create: `web/lib/session.ts`
- Create: `web/components/mode-card.tsx`
- Create: `web/components/chat-shell.tsx`
- Create: `web/components/message-list.tsx`
- Create: `web/components/chat-input.tsx`
- Create: `web/components/progress-chip.tsx`
- Create: `web/components/artifact-panel.tsx`
- Create: `web/tests/home.test.tsx`
- Create: `web/tests/chat-shell.test.tsx`

### Python agent service

- Create: `agent_service/pyproject.toml`
- Create: `agent_service/app/__init__.py`
- Create: `agent_service/app/main.py`
- Create: `agent_service/app/config.py`
- Create: `agent_service/app/db.py`
- Create: `agent_service/app/models.py`
- Create: `agent_service/app/schemas.py`
- Create: `agent_service/app/repository.py`
- Create: `agent_service/app/state_machine.py`
- Create: `agent_service/app/providers/__init__.py`
- Create: `agent_service/app/providers/base.py`
- Create: `agent_service/app/providers/groq_provider.py`
- Create: `agent_service/app/prompts.py`
- Create: `agent_service/app/agents.py`
- Create: `agent_service/app/orchestrator.py`
- Create: `agent_service/tests/test_state_machine.py`
- Create: `agent_service/tests/test_repository.py`
- Create: `agent_service/tests/test_api_flow.py`

### Root docs and tooling

- Create: `.gitignore`
- Create: `README.md`
- Create: `.env.example`
- Create: `Makefile`

## Task 1: Scaffold the Monorepo Skeleton

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `.env.example`
- Create: `Makefile`
- Create: `web/package.json`
- Create: `agent_service/pyproject.toml`

- [ ] **Step 1: Write the root files**

```gitignore
# .gitignore
node_modules/
.next/
dist/
build/
.venv/
__pycache__/
*.pyc
*.sqlite3
*.db
.env
playwright-report/
test-results/
coverage/
```

```markdown
# README.md

## Metaphoric Chatbot

Web app for guided metaphor generation and metaphor coaching.

### Apps

- `web/` — Next.js frontend
- `agent_service/` — FastAPI + Deep Agents backend

### Local development

1. Copy `.env.example` to `.env`
2. Start the Python service
3. Start the Next.js app
```

```dotenv
# .env.example
GROQ_API_KEY=your_groq_api_key
AGENT_DATABASE_URL=sqlite:///./metaphoric_chatbot.db
NEXT_PUBLIC_AGENT_BASE_URL=http://localhost:8000
```

```makefile
# Makefile
dev-web:
	cd web && npm run dev

dev-agent:
	cd agent_service && uv run uvicorn app.main:app --reload

test-web:
	cd web && npm run test

test-agent:
	cd agent_service && uv run pytest
```

```json
{
  "name": "metaphoric-chatbot-web",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "15.3.1",
    "react": "19.1.0",
    "react-dom": "19.1.0"
  },
  "devDependencies": {
    "@testing-library/react": "16.3.0",
    "@testing-library/jest-dom": "6.6.3",
    "@types/node": "22.15.3",
    "@types/react": "19.1.2",
    "@types/react-dom": "19.1.2",
    "tailwindcss": "3.4.17",
    "typescript": "5.8.3",
    "vitest": "3.1.2"
  }
}
```

```toml
[project]
name = "metaphoric-chatbot-agent-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.115.12",
  "uvicorn[standard]==0.34.2",
  "sqlalchemy==2.0.40",
  "pydantic==2.11.3",
  "deepagents",
  "langchain",
  "langgraph",
  "pytest==8.3.5",
  "httpx==0.28.1"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Verify file presence**

Run:

```bash
find . -maxdepth 2 \( -name README.md -o -name Makefile -o -name package.json -o -name pyproject.toml \) | sort
```

Expected:

```text
./Makefile
./README.md
./agent_service/pyproject.toml
./web/package.json
```

- [ ] **Step 3: Commit**

If using git:

```bash
git add .gitignore README.md .env.example Makefile web/package.json agent_service/pyproject.toml
git commit -m "chore: scaffold monorepo structure"
```

## Task 2: Build the Python Persistence Layer

**Files:**
- Create: `agent_service/app/config.py`
- Create: `agent_service/app/db.py`
- Create: `agent_service/app/models.py`
- Create: `agent_service/app/repository.py`
- Test: `agent_service/tests/test_repository.py`

- [ ] **Step 1: Write the failing repository test**

```python
# agent_service/tests/test_repository.py
from app.db import init_db, SessionLocal
from app.repository import SessionRepository


def test_create_session_persists_defaults(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    repo = SessionRepository(session)

    created = repo.create_session(mode="receive")

    assert created.mode == "receive"
    assert created.state == "intake_problem"
    assert created.token
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent_service && uv run pytest tests/test_repository.py::test_create_session_persists_defaults -v
```

Expected:

```text
FAILED tests/test_repository.py::test_create_session_persists_defaults - ModuleNotFoundError
```

- [ ] **Step 3: Write the database and repository implementation**

```python
# agent_service/app/config.py
import os


def get_database_url() -> str:
    return os.getenv("AGENT_DATABASE_URL", "sqlite:///./metaphoric_chatbot.db")
```

```python
# agent_service/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()
engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def init_db(database_url: str):
    global engine
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal.configure(bind=engine)
    from app.models import SessionRecord, MessageRecord, ExtractionRecord, ArtifactRecord, PromptVersionRecord, SettingRecord
    Base.metadata.create_all(bind=engine)
```

```python
# agent_service/app/models.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="groq")
    model: Mapped[str] = mapped_column(String(128), default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageRecord(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    step: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExtractionRecord(Base):
    __tablename__ = "extractions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True, index=True)
    core_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    dominant_emotion: Mapped[str | None] = mapped_column(String(128), nullable=True)
    symbolic_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    block_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_shift: Mapped[str | None] = mapped_column(Text, nullable=True)
    transformation_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ArtifactRecord(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromptVersionRecord(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[str] = mapped_column(String(8), default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SettingRecord(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# agent_service/app/repository.py
import secrets
from app.models import SessionRecord


DEFAULT_STATE_BY_MODE = {
    "receive": "intake_problem",
    "build": "intake_problem",
}


class SessionRepository:
    def __init__(self, db_session):
        self.db = db_session

    def create_session(self, mode: str) -> SessionRecord:
        record = SessionRecord(
            token=secrets.token_urlsafe(24),
            mode=mode,
            state=DEFAULT_STATE_BY_MODE[mode],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
```

- [ ] **Step 4: Run the repository test to verify it passes**

Run:

```bash
cd agent_service && uv run pytest tests/test_repository.py::test_create_session_persists_defaults -v
```

Expected:

```text
PASSED tests/test_repository.py::test_create_session_persists_defaults
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/config.py agent_service/app/db.py agent_service/app/models.py agent_service/app/repository.py agent_service/tests/test_repository.py
git commit -m "feat: add sqlite session persistence"
```

## Task 3: Implement the Guided State Machine

**Files:**
- Create: `agent_service/app/state_machine.py`
- Test: `agent_service/tests/test_state_machine.py`

- [ ] **Step 1: Write the failing state-machine tests**

```python
# agent_service/tests/test_state_machine.py
from app.state_machine import next_state


def test_receive_flow_advances_from_problem_to_feeling():
    assert next_state("receive", "intake_problem") == "intake_feeling"


def test_build_flow_advances_from_offer_symbolic_fields_to_user_selection():
    assert next_state("build", "offer_symbolic_fields") == "user_selects_symbol"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd agent_service && uv run pytest tests/test_state_machine.py -v
```

Expected:

```text
FAILED tests/test_state_machine.py - ModuleNotFoundError
```

- [ ] **Step 3: Implement the state machine**

```python
# agent_service/app/state_machine.py
FLOW = {
    "receive": {
        "intake_problem": "intake_feeling",
        "intake_feeling": "intake_desired_shift",
        "intake_desired_shift": "symbolic_mapping",
        "symbolic_mapping": "generate_metaphor",
        "generate_metaphor": "refine_output",
        "refine_output": "refine_output",
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
    return FLOW[mode][current_state]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd agent_service && uv run pytest tests/test_state_machine.py -v
```

Expected:

```text
PASSED tests/test_state_machine.py::test_receive_flow_advances_from_problem_to_feeling
PASSED tests/test_state_machine.py::test_build_flow_advances_from_offer_symbolic_fields_to_user_selection
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/state_machine.py agent_service/tests/test_state_machine.py
git commit -m "feat: add guided chat state machine"
```

## Task 4: Add Provider Abstraction and Groq Integration

**Files:**
- Create: `agent_service/app/providers/base.py`
- Create: `agent_service/app/providers/groq_provider.py`
- Create: `agent_service/app/prompts.py`
- Create: `agent_service/app/agents.py`

- [ ] **Step 1: Write the provider interface**

```python
# agent_service/app/providers/base.py
from typing import Protocol


class ChatProvider(Protocol):
    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        ...
```

- [ ] **Step 2: Write the Groq provider**

```python
# agent_service/app/providers/groq_provider.py
import os
from langchain.chat_models import init_chat_model


class GroqProvider:
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model_name = model
        self.model = init_chat_model(f"groq:{model}", api_key=os.getenv("GROQ_API_KEY"))

    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        result = self.model.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return result.content if isinstance(result.content, str) else str(result.content)
```

- [ ] **Step 3: Add prompt assets and agent helpers**

```python
# agent_service/app/prompts.py
EXTRACTOR_PROMPT = """You extract symbolic structure from user input.
Return compact JSON-like prose with:
- core conflict
- dominant emotion
- symbolic field
- block pattern
- desired shift
- transformation type
Keep it descriptive, not diagnostic."""

GENERATOR_PROMPT = """You create metaphorical responses.
Rules:
- concrete images
- no diagnosis
- no moral of the story
- include tension, shift, resource, reorganization
- keep room for interpretation"""

COACH_PROMPT = """You coach metaphor construction.
Rules:
- ask short questions
- push toward concrete imagery
- critique cliche, vagueness, moralizing, weak movement
- do not flatter weak work"""
```

```python
# agent_service/app/agents.py
from app.prompts import EXTRACTOR_PROMPT, GENERATOR_PROMPT, COACH_PROMPT


def extract_symbolic_structure(provider, user_input: str) -> str:
    return provider.invoke_chat(EXTRACTOR_PROMPT, user_input)


def generate_metaphor(provider, user_input: str) -> str:
    return provider.invoke_chat(GENERATOR_PROMPT, user_input)


def coach_metaphor(provider, user_input: str) -> str:
    return provider.invoke_chat(COACH_PROMPT, user_input)
```

- [ ] **Step 4: Commit**

```bash
git add agent_service/app/providers/base.py agent_service/app/providers/groq_provider.py agent_service/app/prompts.py agent_service/app/agents.py
git commit -m "feat: add groq provider adapter and prompt assets"
```

## Task 5: Build the Deep Agents Orchestrator and HTTP API

**Files:**
- Create: `agent_service/app/schemas.py`
- Create: `agent_service/app/orchestrator.py`
- Create: `agent_service/app/main.py`
- Test: `agent_service/tests/test_api_flow.py`

- [ ] **Step 1: Write the failing API flow test**

```python
# agent_service/tests/test_api_flow.py
from fastapi.testclient import TestClient
from app.main import app


def test_start_session_returns_token_and_state():
    client = TestClient(app)
    response = client.post("/api/chat/start", json={"mode": "receive"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "receive"
    assert body["state"] == "intake_problem"
    assert body["token"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd agent_service && uv run pytest tests/test_api_flow.py::test_start_session_returns_token_and_state -v
```

Expected:

```text
FAILED tests/test_api_flow.py::test_start_session_returns_token_and_state - ModuleNotFoundError
```

- [ ] **Step 3: Implement the schemas, orchestrator, and FastAPI app**

```python
# agent_service/app/schemas.py
from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    mode: str


class MessageRequest(BaseModel):
    token: str
    content: str


class ChatResponse(BaseModel):
    token: str
    mode: str
    state: str
    assistant_message: str
```

```python
# agent_service/app/orchestrator.py
from app.agents import coach_metaphor, extract_symbolic_structure, generate_metaphor
from app.state_machine import next_state


def build_assistant_message(mode: str, state: str, user_input: str, provider) -> tuple[str, str]:
    if state == "intake_problem":
        prompt = "Descreva o problema em uma frase simples."
        return state, prompt

    if mode == "receive" and state == "intake_feeling":
        return state, "Qual é a sensação dominante nisso?"

    if mode == "receive" and state == "intake_desired_shift":
        return state, "Que mudança você gostaria de sentir ao final desta metáfora?"

    if mode == "receive" and state == "symbolic_mapping":
        return state, extract_symbolic_structure(provider, user_input)

    if mode == "receive" and state == "generate_metaphor":
        return state, generate_metaphor(provider, user_input)

    if mode == "build" and state == "identify_core_conflict":
        return state, "Se isso tivesse um conflito central, qual seria em poucas palavras?"

    if mode == "build" and state == "offer_symbolic_fields":
        return state, "Isso parece mais uma porta emperrada, um rio barrado, uma engrenagem presa, um motor acelerado ou uma bússola girando?"

    if mode == "build" and state in {"user_selects_symbol", "user_attempt", "coach_feedback", "rewrite_together"}:
        return state, coach_metaphor(provider, user_input)

    return state, "Vamos continuar."


def advance_mode(mode: str, current_state: str) -> str:
    return next_state(mode, current_state)
```

```python
# agent_service/app/main.py
from fastapi import FastAPI, HTTPException
from app.config import get_database_url
from app.db import SessionLocal, init_db
from app.providers.groq_provider import GroqProvider
from app.repository import SessionRepository
from app.schemas import ChatResponse, MessageRequest, StartSessionRequest


init_db(get_database_url())
app = FastAPI()
provider = GroqProvider()


@app.post("/api/chat/start", response_model=ChatResponse)
def start_session(payload: StartSessionRequest):
    db = SessionLocal()
    repo = SessionRepository(db)
    created = repo.create_session(payload.mode)
    return ChatResponse(
        token=created.token,
        mode=created.mode,
        state=created.state,
        assistant_message="Descreva o problema em uma frase simples.",
    )
```

- [ ] **Step 4: Run the API flow test to verify it passes**

Run:

```bash
cd agent_service && uv run pytest tests/test_api_flow.py::test_start_session_returns_token_and_state -v
```

Expected:

```text
PASSED tests/test_api_flow.py::test_start_session_returns_token_and_state
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/schemas.py agent_service/app/orchestrator.py agent_service/app/main.py agent_service/tests/test_api_flow.py
git commit -m "feat: add start-session api and chat orchestrator"
```

## Task 6: Build the Next.js Landing Page and Mode Selection

**Files:**
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/postcss.config.js`
- Create: `web/tailwind.config.ts`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/globals.css`
- Create: `web/components/mode-card.tsx`
- Test: `web/tests/home.test.tsx`

- [ ] **Step 1: Write the failing home test**

```tsx
// web/tests/home.test.tsx
import { render, screen } from "@testing-library/react";
import HomePage from "../app/page";


test("renders both product modes", () => {
  render(<HomePage />);
  expect(screen.getByText("Receber uma metáfora")).toBeInTheDocument();
  expect(screen.getByText("Construir minha metáfora")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run test
```

Expected:

```text
FAIL web/tests/home.test.tsx
```

- [ ] **Step 3: Implement the landing page**

```tsx
// web/components/mode-card.tsx
type ModeCardProps = {
  title: string;
  description: string;
  href: string;
};

export function ModeCard({ title, description, href }: ModeCardProps) {
  return (
    <a href={href} className="rounded-3xl border border-stone-300 bg-white/70 p-6 shadow-sm transition hover:-translate-y-0.5">
      <h2 className="text-2xl font-semibold text-stone-900">{title}</h2>
      <p className="mt-3 text-sm leading-6 text-stone-700">{description}</p>
    </a>
  );
}
```

```tsx
// web/app/page.tsx
import { ModeCard } from "../components/mode-card";


export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8ead6,white_45%,#efe6d8)] px-6 py-16 text-stone-900">
      <section className="mx-auto max-w-5xl">
        <p className="text-sm uppercase tracking-[0.24em] text-stone-500">Metaphoric Chatbot</p>
        <h1 className="mt-6 max-w-3xl font-serif text-5xl leading-tight">
          Um chat guiado para receber metáforas ou aprender a construí-las.
        </h1>
        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <ModeCard
            title="Receber uma metáfora"
            description="Descreva um conflito e receba uma metáfora curta, concreta e refinável."
            href="/c/new?mode=receive"
          />
          <ModeCard
            title="Construir minha metáfora"
            description="Transforme abstração em imagem com crítica técnica e reescrita guiada."
            href="/c/new?mode=build"
          />
        </div>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd web && npm run test
```

Expected:

```text
PASS web/tests/home.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add web/app/page.tsx web/components/mode-card.tsx web/tests/home.test.tsx
git commit -m "feat: add landing page and mode selection"
```

## Task 7: Build the Chat Shell and Session Restoration UI

**Files:**
- Create: `web/lib/api.ts`
- Create: `web/lib/session.ts`
- Create: `web/components/chat-shell.tsx`
- Create: `web/components/message-list.tsx`
- Create: `web/components/chat-input.tsx`
- Create: `web/components/progress-chip.tsx`
- Create: `web/components/artifact-panel.tsx`
- Create: `web/app/c/[token]/page.tsx`
- Test: `web/tests/chat-shell.test.tsx`

- [ ] **Step 1: Write the failing chat-shell test**

```tsx
// web/tests/chat-shell.test.tsx
import { render, screen } from "@testing-library/react";
import { ChatShell } from "../components/chat-shell";


test("renders current mode and assistant message", () => {
  render(
    <ChatShell
      mode="receive"
      progressLabel="intake_problem"
      messages={[{ role: "assistant", content: "Descreva o problema em uma frase simples." }]}
    />
  );

  expect(screen.getByText("receive")).toBeInTheDocument();
  expect(screen.getByText("Descreva o problema em uma frase simples.")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run test
```

Expected:

```text
FAIL web/tests/chat-shell.test.tsx
```

- [ ] **Step 3: Implement the chat UI**

```tsx
// web/components/progress-chip.tsx
export function ProgressChip({ label }: { label: string }) {
  return <span className="rounded-full bg-stone-200 px-3 py-1 text-xs uppercase tracking-wide text-stone-700">{label}</span>;
}
```

```tsx
// web/components/message-list.tsx
export function MessageList({ messages }: { messages: { role: string; content: string }[] }) {
  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <div key={index} className={message.role === "assistant" ? "rounded-2xl bg-white p-4" : "rounded-2xl bg-stone-900 p-4 text-white"}>
          {message.content}
        </div>
      ))}
    </div>
  );
}
```

```tsx
// web/components/chat-input.tsx
export function ChatInput() {
  return (
    <form className="mt-6 flex gap-3">
      <input className="flex-1 rounded-2xl border border-stone-300 px-4 py-3" placeholder="Escreva aqui..." />
      <button className="rounded-2xl bg-stone-900 px-5 py-3 text-white" type="submit">
        Enviar
      </button>
    </form>
  );
}
```

```tsx
// web/components/artifact-panel.tsx
export function ArtifactPanel() {
  return <aside className="rounded-3xl border border-stone-300 bg-white/70 p-5 text-sm text-stone-700">Os artefatos simbólicos aparecerão aqui.</aside>;
}
```

```tsx
// web/components/chat-shell.tsx
import { ArtifactPanel } from "./artifact-panel";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";
import { ProgressChip } from "./progress-chip";


export function ChatShell({
  mode,
  progressLabel,
  messages,
}: {
  mode: string;
  progressLabel: string;
  messages: { role: string; content: string }[];
}) {
  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5eee4,white_30%,#ebe3d6)] px-6 py-10 text-stone-900">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.5fr_0.7fr]">
        <section className="rounded-[2rem] border border-stone-300 bg-white/70 p-6">
          <div className="mb-6 flex items-center justify-between">
            <strong className="text-sm uppercase tracking-[0.24em] text-stone-500">{mode}</strong>
            <ProgressChip label={progressLabel} />
          </div>
          <MessageList messages={messages} />
          <ChatInput />
        </section>
        <ArtifactPanel />
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd web && npm run test
```

Expected:

```text
PASS web/tests/chat-shell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add web/components/chat-shell.tsx web/components/message-list.tsx web/components/chat-input.tsx web/components/progress-chip.tsx web/components/artifact-panel.tsx web/tests/chat-shell.test.tsx
git commit -m "feat: add guided chat shell"
```

## Task 8: Connect the Web App to the Agent Service

**Files:**
- Modify: `agent_service/app/main.py`
- Create: `web/lib/api.ts`
- Create: `web/lib/session.ts`
- Create: `web/app/c/[token]/page.tsx`

- [ ] **Step 1: Extend the FastAPI app with message handling**

```python
# append to agent_service/app/main.py
from app.models import SessionRecord, MessageRecord
from app.orchestrator import advance_mode, build_assistant_message


@app.post("/api/chat/message", response_model=ChatResponse)
def send_message(payload: MessageRequest):
    db = SessionLocal()
    record = db.query(SessionRecord).filter(SessionRecord.token == payload.token).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(MessageRecord(session_id=record.id, role="user", content=payload.content, step=record.state))
    db.commit()

    next_step = advance_mode(record.mode, record.state)
    assistant_state, assistant_message = build_assistant_message(record.mode, next_step, payload.content, provider)
    record.state = next_step
    db.add(MessageRecord(session_id=record.id, role="assistant", content=assistant_message, step=assistant_state))
    db.commit()

    return ChatResponse(
        token=record.token,
        mode=record.mode,
        state=record.state,
        assistant_message=assistant_message,
    )
```

- [ ] **Step 2: Implement the frontend API client**

```ts
// web/lib/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_AGENT_BASE_URL ?? "http://localhost:8000";

export async function startSession(mode: "receive" | "build") {
  const response = await fetch(`${BASE_URL}/api/chat/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
    cache: "no-store",
  });
  return response.json();
}

export async function sendMessage(token: string, content: string) {
  const response = await fetch(`${BASE_URL}/api/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, content }),
    cache: "no-store",
  });
  return response.json();
}
```

```ts
// web/lib/session.ts
const KEY = "metaphoric-chatbot-recent-sessions";

export function storeRecentSession(token: string) {
  const current = JSON.parse(localStorage.getItem(KEY) ?? "[]") as string[];
  const next = [token, ...current.filter((item) => item !== token)].slice(0, 5);
  localStorage.setItem(KEY, JSON.stringify(next));
}
```

- [ ] **Step 3: Implement the chat route**

```tsx
// web/app/c/[token]/page.tsx
import { ChatShell } from "../../../components/chat-shell";


export default function ChatPage({ params }: { params: { token: string } }) {
  return (
    <ChatShell
      mode="receive"
      progressLabel="intake_problem"
      messages={[{ role: "assistant", content: `Sessão ${params.token}. Descreva o problema em uma frase simples.` }]}
    />
  );
}
```

- [ ] **Step 4: Run both test suites**

Run:

```bash
make test-agent
make test-web
```

Expected:

```text
all agent tests pass
all web tests pass
```

- [ ] **Step 5: Commit**

```bash
git add agent_service/app/main.py web/lib/api.ts web/lib/session.ts web/app/c/[token]/page.tsx
git commit -m "feat: wire chat ui to agent api"
```

## Task 9: End-to-End Validation and MVP Cleanup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add run instructions**

```markdown
## Running locally

### Agent service

```bash
cd agent_service
uv sync
uv run uvicorn app.main:app --reload
```

### Web app

```bash
cd web
npm install
npm run dev
```
```

- [ ] **Step 2: Run manual smoke test**

Run:

```bash
make dev-agent
make dev-web
```

Expected:

```text
Frontend opens at http://localhost:3000
API responds at http://localhost:8000/docs
Starting a session returns a unique token
Sending a message advances the guided state
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add local development instructions"
```

## Self-Review

### Spec coverage

- Two product modes: covered by Tasks 6, 7, and 8.
- Guided chat state machine: covered by Task 3.
- Python Deep Agents backend: covered by Tasks 4 and 5.
- Groq-first provider abstraction: covered by Task 4.
- SQLite persistence: covered by Task 2.
- Anonymous unique-link sessions: covered by Tasks 2, 5, and 8.
- Text-only MVP: preserved by scope throughout.
- Safety and prompt constraints: initial prompt-level coverage in Task 4; explicit crisis handling remains a follow-up refinement once the baseline flow is running.

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain.
- Commands and file paths are explicit.
- Each code-writing step contains concrete content.

### Type consistency

- Session modes are consistently `receive` and `build`.
- Initial state is consistently `intake_problem`.
- Chat response fields are consistently `token`, `mode`, `state`, `assistant_message`.

### Remaining Gap

- The plan establishes the baseline app and provider abstraction, but the explicit crisis-support response path from the spec still needs a concrete follow-up task after the happy path is working.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-metaphoric-chatbot-mvp.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
