## Metaphoric Chatbot

Web app for guided metaphor generation and metaphor coaching.

### Apps

- `web/` — Next.js frontend
- `agent_service/` — FastAPI + Deep Agents backend

### Local development

```bash
cp .env.example .env
(cd web && npm install)
(cd agent_service && uv sync --extra test --extra lint)
```

### Run the agent service

```bash
cd agent_service
uv run uvicorn app.main:app --reload
```

### Run the web app

```bash
cd web
npm run dev
```

### Tests

```bash
cd agent_service
uv run ruff format .
uv run ruff check .
uv run pytest

cd ../web
npm test
```

### Pre-commit

```bash
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

The local hooks run the shared hygiene checks plus `ruff format`, `ruff`, and `pytest` for `agent_service`, and `vitest` for `web`. The GitHub Actions workflow runs the same Python format/lint/test checks, plus the web build and any `lint` or `typecheck` scripts that may be added later.

### Receive Mode Notes

Receive mode now interprets user turns semantically. Changes in `agent_service/app/prompts.py`, `agent_service/app/agents.py`, `agent_service/app/orchestrator.py`, or `agent_service/app/providers/local_provider.py` must preserve this rule:

- user-supplied metaphors become the active refinement seed instead of being discarded for generic menu choices
- receive artifacts in the contextual path should avoid rigid `A/B/C` quiz framing
