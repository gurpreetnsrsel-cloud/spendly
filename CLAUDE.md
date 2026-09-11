# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Flask-based personal expense tracker, built incrementally as a staged learning project ("Step 1", "Step 3", etc. appear in code comments and placeholder routes). Not all functionality exists yet — many routes in `app.py` are intentional placeholders returning plain strings until their corresponding step is implemented.

## Commands

```bash
# Activate the venv (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server (http://localhost:5001)
python app.py

# Run tests
pytest
```

There is no build step, linter config, or frontend bundler — templates and static assets are served directly by Flask.

## Architecture

- `app.py` — single Flask application entrypoint; all routes are defined here (no blueprints). Runs on port 5001 with debug mode on.
- `database/db.py` — intended to hold `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (creates tables with `CREATE TABLE IF NOT EXISTS`), and `seed_db()` (sample data for dev). As of now this file is an empty stub — implementing it is a pending step.
- `templates/` — Jinja2 templates. `base.html` defines the shared layout (nav, footer, font imports) and is extended by page templates via `{% block content %}` / `{% block title %}` / `{% block head %}` / `{% block scripts %}`.
- `static/css/style.css`, `static/js/main.js` — global stylesheet and script, referenced from `base.html`.
- `expense_tracker.db` — SQLite database file (gitignored, created at runtime by `init_db()`).

## Current state of routes

Implemented (render real templates): `/`, `/register`, `/login`, `/terms`, `/privacy`.

Placeholder only (return a plain string, no template/logic yet): `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`. When asked to implement one of these, expect to also need the database layer (`database/db.py`) and likely session/auth handling, since none of that exists yet.

## Conventions

- Brand name in UI copy/templates is "Spendly".
- Route handler functions use plain, descriptive names matching the URL (e.g., `add_expense` for `/expenses/add`) — keep this pattern for new routes.
