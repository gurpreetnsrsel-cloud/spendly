# Spec: Edit Expense

## Overview

Step 8 implements the "Edit Expense" feature, replacing the placeholder
`GET /expenses/<id>/edit` route with a real form that lets a logged-in user
update an existing expense they own. This builds on Step 7 (Add Expense),
reusing the same form pattern and validation rules, and lays the groundwork
for the delete route (Step 9) that follows.

## Depends on

- Step 1: Database setup (`expenses` table and `get_db()` exist)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the current user)
- Step 5: Backend connection (`database/queries.py` pattern for DB helpers)
- Step 7: Add Expense (`insert_expense`, `add_expense.html` form pattern,
  amount/category/date validation rules to reuse)

## Routes

- `GET /expenses/<id>/edit` — render the edit form pre-filled with the
  expense's current values — logged-in, owner only
- `POST /expenses/<id>/edit` — validate and update the expense, then redirect
  to `/profile` — logged-in, owner only

## Database changes

No database changes. The `expenses` table (`user_id`, `amount`, `category`,
`date`, `description`, `created_at`) already supports everything this form
needs.

## Templates

- **Create:** `templates/edit_expense.html` — form with fields for amount,
  category (select, populated from `database.db.CATEGORIES`), date, and
  description (optional), pre-filled with the expense's existing values;
  modeled on `templates/add_expense.html`
- **Modify:** `templates/profile.html` — add an "Edit" link per transaction
  row pointing to `{{ url_for('edit_expense', id=transaction.id) }}`

## Files to change

- `app.py` — replace the placeholder `edit_expense(id)` view with `GET`/`POST`
  handling: auth check, ownership check, form validation, update, redirect
- `templates/profile.html` — add the "Edit" entry point per transaction row
- `database/queries.py` — add `get_expense_by_id(expense_id, user_id)` and
  `update_expense(expense_id, user_id, amount, category, date, description)`;
  modify `get_recent_transactions` to also select and return each
  transaction's `id` (needed by `profile.html` to build the edit link)

## Files to create

- `templates/edit_expense.html`

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
- `category` must be validated against `database.db.CATEGORIES` — reject
  anything not in that list
- `amount` must be validated as a positive number (reject zero, negative,
  non-numeric input) before update
- `date` must be validated as a real calendar date (`YYYY-MM-DD`); reject
  malformed or missing values
- On any validation error, re-render `edit_expense.html` with the entered
  values preserved and an error message — never lose user input
- `GET /expenses/<id>/edit` and `POST /expenses/<id>/edit` must redirect
  unauthenticated users to `/login`, matching the pattern used by `/profile`
- If the expense does not exist, or exists but belongs to a different user,
  return a 404 — never reveal another user's expense data or allow editing it
- `get_expense_by_id` and `update_expense` in `database/queries.py` must
  filter by both `id` and `user_id` in the `WHERE` clause (not just `id`) to
  enforce ownership at the query level
- `update_expense` must call `get_db()` internally, commit, and close the
  connection before returning

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by the current user
      shows a form pre-filled with its amount, category, date, and description
- [ ] Visiting `/expenses/<id>/edit` for a non-existent expense id returns 404
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by another user
      returns 404
- [ ] Submitting the form with valid data updates the existing row (not a new
      insert) and redirects to `/profile`
- [ ] The updated expense's new values appear in the profile page's
      transaction list and are reflected in the summary stats and category
      breakdown
- [ ] Submitting with a missing/zero/negative amount re-shows the form with
      an error and the row is left unchanged
- [ ] Submitting with a category not in `database.db.CATEGORIES` re-shows the
      form with an error and the row is left unchanged
- [ ] Submitting with an invalid or missing date re-shows the form with an
      error and the row is left unchanged
- [ ] The profile page has a visible "Edit" link per transaction that
      navigates to `/expenses/<id>/edit`
