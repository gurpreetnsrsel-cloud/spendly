# Spec: Login and Logout

## Overview

This step implements real sign-in and sign-out for Spendly. The `/login` page and form already exist (`templates/login.html` posts `email` and `password` to `/login` and renders `{{ error }}`), but `app.py` only has a `GET /login` route and `/logout` is a placeholder string. This step adds `POST /login` (verify credentials against the `users` table, start a session) and a real `/logout` (clear the session, redirect home), and makes the navbar reflect auth state. Registration (Step 2) already stores `user_id` in `session`; this step completes the auth loop so later gated features (profile, expenses) can rely on it.

## Depends on

- Step 1 — Database setup (`get_db`, `users` table) — complete.
- Step 2 — Registration (users with hashed passwords, `session["user_id"]`, `app.secret_key`) — complete.

## Routes

- `GET /login` — render the sign-in form; if already logged in, redirect to `/profile` — public (existing, small change)
- `POST /login` — validate email/password, verify hash, set `session["user_id"]`, redirect to `/profile` — public
- `GET /logout` — clear the session and redirect to `/` — logged-in (harmless if called while logged out; simply redirects)

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) is sufficient. Verified against `database/db.py`.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — repopulate the `email` input on failed login (`value="{{ email or '' }}"`); never repopulate the password.
  - `templates/base.html` — in the navbar, when `session.user_id` is set show "Profile" and "Sign out" (`url_for('logout')`) links instead of "Sign in" / "Get started".

## Files to change

- `app.py` — add `POST` handling to `login`, redirect-if-authenticated on GET, implement `logout`.
- `templates/login.html` — repopulate email on error.
- `templates/base.html` — auth-aware navbar.

## Files to create

- `tests/test_login_logout.py` — pytest suite using a temporary database (patches `database.db.DB_PATH`, same approach as `tests/test_registration.py`).

## New dependencies

No new dependencies. Use `werkzeug.security.check_password_hash` and Flask's built-in `session`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (verify with `check_password_hash`; never compare plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Normalise the email (`strip().lower()`) before lookup, matching registration
- Use one generic error for both unknown email and wrong password ("Invalid email or password.") so account existence is not leaked; a missing field gives "Please fill in all fields."
- Call `session.clear()` before setting `session["user_id"]` on successful login
- Close DB connections with `closing(get_db())`, consistent with `register`
- Do not open-redirect: always redirect to the fixed `profile` route after login (no `next` parameter in this step)
- `/profile` remains a placeholder route; leave it as-is, just ensure the redirect target exists

## Definition of done

- [ ] Signing in as the seeded demo user (`demo@spendly.com` / `demo123`) redirects to `/profile` and `session` contains the user's id
- [ ] Signing in with a newly registered user's credentials works
- [ ] Email matching is case-insensitive and ignores surrounding whitespace
- [ ] Wrong password and unknown email both re-render the login form with "Invalid email or password."
- [ ] Submitting with an empty field re-renders the form with "Please fill in all fields." instead of crashing
- [ ] After a failed login the email field is repopulated and the password field is empty
- [ ] Visiting `/login` while logged in redirects to `/profile`
- [ ] Visiting `/logout` clears the session and redirects to `/`; afterwards `session` has no `user_id`
- [ ] The navbar shows "Sign in" / "Get started" when logged out and "Profile" / "Sign out" when logged in
- [ ] No plaintext password appears in the database or server logs
- [ ] `pytest` passes, including the new login/logout tests
