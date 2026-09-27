# Spec: Delete Expense

## Overview

Step 9 implements the "Delete Expense" feature, replacing the placeholder
`GET /expenses/<id>/delete` route with a real action that lets a logged-in
user permanently remove an expense they own. This is the last of the core
CRUD operations on expenses, following the same ownership and validation
patterns established by Add Expense (Step 7) and Edit Expense (Step 8).

## Depends on

- Step 1: Database setup (`expenses` table and `get_db()` exist)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the current user)
- Step 5: Backend connection (`database/queries.py` pattern for DB helpers)
- Step 7: Add Expense (`insert_expense` pattern to mirror)
- Step 8: Edit Expense (`get_expense_by_id` ownership-check pattern, and the
  transaction row's per-row actions in `profile.html` to extend)

## Routes

- `POST /expenses/<id>/delete` — delete the expense, then redirect to
  `/profile` — logged-in, owner only

The existing placeholder is a bare `GET` route. It will be changed to
`POST` only (no GET handling) since deletion is a destructive action and
must not be triggerable by a plain link/prefetch.

## Database changes

No database changes. The `expenses` table already supports deletion via its
existing `id`/`user_id` columns.

## Templates

- **Create:** None
- **Modify:** `templates/profile.html` — add a "Delete" action per
  transaction row, submitted via a small inline `<form method="post"
  action="{{ url_for('delete_expense', id=tx.id) }}">` next to the existing
  "Edit" link, with a confirmation prompt (e.g. `onsubmit="return
  confirm(...)"`) before submitting

## Files to change

- `app.py` — replace the placeholder `delete_expense(id)` view with a
  `POST`-only handler: auth check, ownership check, delete, redirect
- `templates/profile.html` — add the "Delete" action per transaction row
- `database/queries.py` — add `delete_expense(expense_id, user_id)`

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- `POST /expenses/<id>/delete` must redirect unauthenticated users to
  `/login`, matching the pattern used by `/profile` and `edit_expense`
- If the expense does not exist, or exists but belongs to a different user,
  return a 404 — never reveal another user's expense data or allow deleting
  it
- `delete_expense` in `database/queries.py` must filter by both `id` and
  `user_id` in the `WHERE` clause (not just `id`) to enforce ownership at
  the query level, and must call `get_db()` internally, commit, and close
  the connection before returning
- The route must only accept `POST` (no `GET` handler) — deleting via a
  plain navigable link is not acceptable
- The delete action in `profile.html` must ask for confirmation before
  submitting (e.g. a JS `confirm()` dialog) to avoid accidental data loss

## Definition of done

- [ ] Submitting `POST /expenses/<id>/delete` while logged out redirects to
      `/login`
- [ ] Submitting `POST /expenses/<id>/delete` for an expense owned by the
      current user removes it from the database and redirects to `/profile`
- [ ] Submitting `POST /expenses/<id>/delete` for a non-existent expense id
      returns 404
- [ ] Submitting `POST /expenses/<id>/delete` for an expense owned by
      another user returns 404 and leaves that expense untouched
- [ ] Sending a `GET` request to `/expenses/<id>/delete` does not delete
      anything (method not allowed)
- [ ] After a successful delete, the removed expense no longer appears in
      the profile page's transaction list, and the summary stats and
      category breakdown reflect its removal
- [ ] The profile page has a visible "Delete" action per transaction row
      that prompts for confirmation before submitting
