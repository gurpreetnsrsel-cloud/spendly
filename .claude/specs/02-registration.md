# Spec: Registration

## Overview

This step implements real user registration for Spendly. The `/register` page and form already exist (`templates/register.html` posts `name`, `email`, `password`, `confirm_password` to `POST /register`), but `app.py` only has a `GET /register` route that renders the template — there is no handler for the form submission. This step adds the `POST /register` route: validate input, hash the password, insert a new row into the `users` table, and start a logged-in session for the new user. It builds directly on the database layer from Step 1 and is the foundation every later auth-gated feature (profile, expenses) depends on.

## Depends on

- Step 1 — Database setup (`database/db.py`: `get_db`, `init_db`, `seed_db`, `users` table) — complete.

## Routes

- `GET /register` — render the registration form — public (already implemented, unchanged)
- `POST /register` — validate submitted fields (including that the password and confirmation match), create the user, log them in, redirect to profile — public

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already supports registration. No migration needed — verified against `database/db.py`.

## Templates

- **Create:** none
- **Modify:** `templates/register.html` — add a "Confirm password" input (`name="confirm_password"`, `type="password"`, `required`, `minlength="8"`) directly below the password field. The form already posts to `/register` and renders `{{ error }}`. Re-render with `error` and previously entered `name`/`email` values on validation failure (e.g. `value="{{ name or '' }}"` on the inputs) so the user doesn't retype everything.

## Files to change

- `app.py` — add `POST` handling to the `/register` route (or a separate view function if a method-based split is cleaner), add password hashing, session creation, and redirect logic.
- `templates/register.html` — add the confirm-password field; repopulate `name`/`email` values (never passwords) on re-render after a validation error.

## Files to create

- `tests/test_registration.py` — pytest suite using a temporary database (patches `database.db.DB_PATH`).

## New dependencies

No new dependencies. Use `werkzeug.security.generate_password_hash` (already used in `database/db.py`) and Flask's built-in `session`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`, min 8 characters enforced server-side, not just via the HTML `required`/pattern attributes)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Require `confirm_password` server-side: reject with "Passwords do not match." when it differs from `password`, and treat an empty confirmation as a missing field. Never echo either password back into the re-rendered form
- Validate `email` uniqueness before inserting; on `sqlite3.IntegrityError` (or a pre-check `SELECT`), re-render `register.html` with a friendly error instead of a 500
- Set `app.secret_key` (from an env var, falling back to a dev default) so `session` works
- On success, store the new user's `id` in `session` and redirect to `/profile` (currently a placeholder route — leave it as-is, just ensure the redirect target exists)

## Definition of done

- [ ] Submitting the register form with valid, unique details creates a row in `users` with a hashed (not plaintext) password
- [ ] Submitting with an email that already exists re-renders `register.html` with an error message and no duplicate row is created
- [ ] The register form shows both "Password" and "Confirm password" fields
- [ ] Submitting with a missing field (including confirm password) or password under 8 characters re-renders the form with an error instead of crashing
- [ ] Submitting with a password and confirmation that do not match re-renders the form with "Passwords do not match." and creates no row
- [ ] After successful registration, the browser is redirected and `session` contains the new user's id
- [ ] Re-running the app and registering multiple distinct users works with no unique-constraint crashes
- [ ] No plaintext password ever appears in the database or in server logs
