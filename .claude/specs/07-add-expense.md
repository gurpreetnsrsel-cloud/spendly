# Spec: Add Expense

## Overview

Step 7 implements the "Add Expense" feature, replacing the placeholder
`GET /expenses/add` route with a real form that lets a logged-in user record
a new expense against their account. This is the first step where users can
write data into the `expenses` table through the UI (previously only the
seed script inserted expenses), and it lays the groundwork for the edit
(Step 8) and delete (Step 9) routes that follow.

## Depends on

- Step 1: Database setup (`expenses` table and `get_db()` exist)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the current user)
- Step 5: Backend connection (`database/queries.py` pattern for DB helpers)

## Routes

- `GET /expenses/add` — render the empty add-expense form — logged-in
- `POST /expenses/add` — validate and insert the new expense, then redirect
  to `/profile` — logged-in

## Database changes

No database changes. The `expenses` table (`user_id`, `amount`, `category`,
`date`, `description`, `created_at`) already supports everything this form
needs.

## Templates

- **Create:** `templates/add_expense.html` — form with fields for amount,
  category (select, populated from `database.db.CATEGORIES`), date
  (defaulting to today), and description (optional)
- **Modify:** `templates/profile.html` — add an "Add Expense" link/button
  pointing to `{{ url_for('add_expense') }}`

## Files to change

- `app.py` — replace the placeholder `add_expense()` view with `GET`/`POST`
  handling: auth check, form validation, insert, redirect
- `templates/profile.html` — add the "Add Expense" entry point

## Files to create

- `templates/add_expense.html`
- `database/queries.py` — add `insert_expense(user_id, amount, category, date, description)`

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
  non-numeric input) before insert
- `date` must be validated as a real calendar date (`YYYY-MM-DD`); reject
  malformed or missing values
- On any validation error, re-render `add_expense.html` with the entered
  values preserved and an error message — never lose user input
- `GET /expenses/add` and `POST /expenses/add` must redirect unauthenticated
  users to `/login`, matching the pattern used by `/profile`
- `insert_expense` in `database/queries.py` must call `get_db()` internally,
  commit, and close the connection before returning

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount,
      category, date, and description fields
- [ ] Submitting the form with valid data inserts a new row into `expenses`
      for the current user and redirects to `/profile`
- [ ] The newly added expense appears in the profile page's transaction list
      and is reflected in the summary stats and category breakdown
- [ ] Submitting with a missing/zero/negative amount re-shows the form with
      an error and no row is inserted
- [ ] Submitting with a category not in `database.db.CATEGORIES` re-shows the
      form with an error and no row is inserted
- [ ] Submitting with an invalid or missing date re-shows the form with an
      error and no row is inserted
- [ ] The profile page has a visible "Add Expense" link that navigates to
      `/expenses/add`
