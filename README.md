## Metaphoric Chatbot

Web app for guided metaphor generation and metaphor coaching.

### Apps

- `web/` — Next.js frontend
- `agent_service/` — FastAPI + Deep Agents backend

### Local development

```bash
cp .env.example .env
(cd web && npm install)
(cd agent_service && uv sync --extra test)
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
uv run pytest

cd ../web
npm test -- --run
```
