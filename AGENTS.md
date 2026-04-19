# Repository Guidelines

## Project Structure & Module Organization
This repository has three active areas:

- `web/`: Next.js 15 + React 19 frontend. Routes live in `web/app/`, shared UI in `web/components/`, helpers in `web/lib/`, and tests in `web/tests/`.
- `agent_service/`: FastAPI backend. Application code lives in `agent_service/app/`; provider integrations are under `agent_service/app/providers/`; tests live in `agent_service/tests/`.
- Root utilities: `convert_books_to_markdown.py` plus root-level `tests/` cover ebook conversion. Planning docs live in `docs/superpowers/`.

Keep generated or local-only artifacts out of commits when possible, including `metaphoric_chatbot.db`, `markdown/`, and temporary validation folders.

## Build, Test, and Development Commands
- `cp .env.example .env`: create local configuration before running services.
- `./dev.sh`: starts the FastAPI service on `:8000` and the web app on `:3000`.
- `cd agent_service && uv sync --extra test --extra lint`: install Python dependencies.
- `cd agent_service && uv run uvicorn app.main:app --reload`: run the API only.
- `cd web && npm install && npm run dev`: install frontend packages and start Next.js.
- `cd agent_service && uv run ruff format . && uv run ruff check . && uv run pytest`: format, lint, and test backend code.
- `cd web && npm test`: run the frontend Vitest suite.
- `pre-commit run --all-files`: run the same checks used in local hooks and CI.

## Coding Style & Naming Conventions
Python targets 3.12+ and is formatted with Ruff (`line-length = 120`). Use type hints, snake_case for functions/modules, and keep FastAPI/Pydantic code in `agent_service/app/`.

TypeScript/React uses 2-space indentation, PascalCase for component files, and camelCase for helpers/hooks. Keep route files under `web/app/**/page.tsx`.

## Testing Guidelines
Place backend tests in `agent_service/tests/` and root conversion tests in `tests/`. Use `test_*.py` naming. Frontend tests live in `web/tests/`; prefer `*.test.ts` or `*.test.tsx` beside the feature area they cover.

Run affected tests before opening a PR. For cross-cutting changes, run both suites.

## Commit & Pull Request Guidelines
Recent history mixes short imperative commits (`Refine navigation...`) with conventional prefixes (`refactor:`). Prefer concise imperative subjects; use a prefix when helpful.

PRs should include:

- a clear summary of user-visible or architectural changes
- linked issue/context when available
- screenshots or short recordings for UI changes
- confirmation that `ruff`, `pytest`, and `npm test` passed for touched areas

## Security & Config Tips
Do not commit `.env` secrets or local database contents. Keep CORS, provider keys, and local storage behavior aligned with `agent_service/app/config.py` and `web/lib/session.ts`.

## Agent-Specific Notes
When improving the chat agent, always consult `livros_metafora/` first. Treat that folder as the primary local reference for refining prompt tone, metaphor quality, coaching behavior, and domain grounding before changing `agent_service/app/agents.py`, `agent_service/app/prompts.py`, or orchestration logic.
