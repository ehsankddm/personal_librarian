# Repository Guidelines

## Project Structure & Module Organization
- `core/`: Messaging, planner, policies, registry, preferences.
- `agents/`: Agent implementations (Planner, Gatekeeper, Curator, Interface, CodeGenerator, Reflection).
- `actions/`: Gatekeeper-executed actions and executor.
- `learning/`: Router learner, telemetry, reward hooks.
- `memory/`: Agent and society memory logs; runtime archives.
- `state/`: Preferences and policies JSON (runtime configuration).
- `ui/`: User-facing interface helpers.
- `agents_generated_specs/`: Draft/accepted capability specs produced by the system.
- Tests: top-level `test_*.py` scripts.

## Build, Test, and Development Commands
- Install deps (uv): `uv sync` or `uv pip install -e ".[dev]"`.
- Run locally: `python run_dev.py` (set `PHASE1_DEV=1` to print LLM context bundles).
- Lint: `ruff check .` | Fix: `ruff check . --fix`.
- Format: `black .` (line length 100).
- Type check: `mypy core agents actions learning`.
- Tests: `pytest -q` or run a script directly (e.g., `python test_planner.py`).

## Coding Style & Naming Conventions
- Python 3.11, spaces, 100-char lines, double quotes (see `pyproject.toml`).
- Use Black + Ruff; fix lint before PRs. Prefer clear, small functions.
- Modules/files: `snake_case.py`; classes: `PascalCase`; functions/vars: `snake_case`.
- Tests: name files `test_*.py`; test functions start with `test_`.
- Agent IDs: `<Role>_<variant>_v<semver>` (e.g., `PlannerAgent_main_v1`). Keep role in `role` and traits in `traits`.

## Testing Guidelines
- Framework: pytest; async tests are supported via script-style runners in this repo.
- Write unit tests near touched areas; prefer deterministic, no network/filesystem without Gatekeeper.
- Run `pytest -q` and ensure scripts like `test_planner.py` succeed locally.

## Commit & Pull Request Guidelines
- Commits: imperative, concise, scoped (e.g., "planner: improve routing for ingestion").
- PRs: include purpose, summary of changes, linked issues, and screenshots/logs if behavior changes.
- Checklist: docs updated (e.g., `README.md`, specs), `ruff`, `black`, `mypy`, and tests all pass.

## Security & Configuration Tips
- Never bypass the Gatekeeper for network, shell, or filesystem actions; use structured ActionRequests.
- Secrets/config: use `.env` (loaded in `run_dev.py`); never commit secrets. Prefer editing JSON under `state/` for policies/preferences.
- Logs are written to `logs/`; memory to `memory/agents/<agent_id>/YYYY-MM-DD.md`.

