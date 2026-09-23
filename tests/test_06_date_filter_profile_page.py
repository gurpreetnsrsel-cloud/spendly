"""Tests for Step 6: date-range filter on the /profile route.

Spec: .claude/specs/06-date-filter-profile-page.md

These tests exercise the documented behaviour of `GET /profile` with the
optional `date_from` / `date_to` query-string parameters. They assert
against the spec's Routes/Rules/Definition-of-Done sections only:

- No params -> identical to the unfiltered (Step 5) view
- Valid range -> summary stats, transaction list, and category breakdown
  are all narrowed to that range
- date_from > date_to -> falls back to unfiltered view + flash error
- Malformed date string -> no crash, falls back to unfiltered view
- Range with zero matches -> Rs0.00 total, 0 transactions, empty category
  breakdown, no errors
- Auth guard -> unauthenticated requests redirect to /login
- Currency symbol (Rs) still present under filtered views
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"

# Expenses spread across several months of 2026 so that date-range filters
# produce clearly distinguishable subsets.
#
# Full (unfiltered) totals: 346.24 total, 8 transactions, 7 categories.
EXPENSES = [
    (49.99, "Food", "2026-01-01", "Groceries"),
    (8.75, "Food", "2026-02-02", "Coffee"),
    (15.50, "Transport", "2026-03-03", "Bus pass"),
    (150.00, "Bills", "2026-06-04", "Electricity bill"),
    (30.00, "Health", "2026-09-05", "Pharmacy"),
    (25.00, "Entertainment", "2026-09-06", "Movie tickets"),
    (57.00, "Shopping", "2026-09-07", "New shoes"),
    (10.00, "Other", "2026-09-08", "Miscellaneous"),
]

# The subset falling inside 2026-09-01..2026-09-08 (inclusive), used for the
# "valid range narrows results" test.
SEPTEMBER_SUBSET = EXPENSES[4:]  # Health, Entertainment, Shopping, Other
SEPTEMBER_TOTAL = "122.00"  # 30 + 25 + 57 + 10
SEPTEMBER_COUNT = 4
SEPTEMBER_CATEGORIES = {"Health", "Entertainment", "Shopping", "Other"}

FULL_TOTAL = "346.24"
FULL_COUNT = 8
FULL_CATEGORIES = {
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
}


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()
    yield db_module


def seed_user(db, with_expenses=True):
    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", EMAIL, generate_password_hash(PASSWORD)),
    )
    user_id = cursor.lastrowid
    if with_expenses:
        for amount, category, expense_date, description in EXPENSES:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, expense_date, description),
            )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture
def client(db):
    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def login(client):
    return client.post("/login", data={"email": EMAIL, "password": PASSWORD})


# --------------------------------------------------------------------- #
# Auth guard                                                            #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "query_string",
    [
        "",
        "?date_from=2026-09-01&date_to=2026-09-08",
        "?date_from=not-a-date",
    ],
)
def test_profile_requires_login_regardless_of_filter_params(client, query_string):
    response = client.get(f"/profile{query_string}")
    assert response.status_code == 302, "Unauthenticated /profile should redirect"
    assert response.headers["Location"].endswith("/login"), (
        "Unauthenticated /profile (with or without filter params) must redirect to /login"
    )


# --------------------------------------------------------------------- #
# No params -> identical to unfiltered (Step 5) behaviour               #
# --------------------------------------------------------------------- #


def test_profile_no_params_matches_unfiltered_view(db, client):
    seed_user(db)
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert FULL_TOTAL in html, "Unfiltered total should include all 8 expenses"
    assert "8" in html, "Unfiltered transaction count should be 8"
    for category in FULL_CATEGORIES:
        assert category in html, f"Unfiltered view should show category {category}"


def test_profile_no_expenses_no_params(db, client):
    seed_user(db, with_expenses=False)
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "0.00" in html


# --------------------------------------------------------------------- #
# Valid date range narrows all three sections                          #
# --------------------------------------------------------------------- #


def test_profile_valid_range_narrows_summary_and_transactions(db, client):
    seed_user(db)
    login(client)
    response = client.get(
        "/profile?date_from=2026-09-01&date_to=2026-09-08"
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert SEPTEMBER_TOTAL in html, "Filtered total should only sum the in-range expenses"
    assert FULL_TOTAL not in html, "Full unfiltered total should not appear in a filtered view"

    for _, _, _, description in SEPTEMBER_SUBSET:
        assert description in html, f"In-range transaction '{description}' should be listed"
    for _, _, _, description in EXPENSES[:4]:
        assert description not in html, (
            f"Out-of-range transaction '{description}' should not be listed"
        )


def test_profile_valid_range_narrows_category_breakdown(db, client):
    seed_user(db)
    login(client)
    response = client.get(
        "/profile?date_from=2026-09-01&date_to=2026-09-08"
    )
    html = response.get_data(as_text=True)

    for category in SEPTEMBER_CATEGORIES:
        assert category in html, f"Filtered breakdown should include {category}"

    out_of_range_categories = FULL_CATEGORIES - SEPTEMBER_CATEGORIES
    for category in out_of_range_categories:
        assert category not in html, (
            f"Filtered breakdown should not include out-of-range category {category}"
        )


def test_profile_valid_range_inclusive_bounds(db, client):
    """date_from/date_to are documented as inclusive bounds."""
    seed_user(db)
    login(client)
    response = client.get(
        "/profile?date_from=2026-09-05&date_to=2026-09-05"
    )
    html = response.get_data(as_text=True)
    assert "Pharmacy" in html, "Expense dated exactly date_from/date_to must be included"
    assert "30.00" in html


# --------------------------------------------------------------------- #
# date_from > date_to                                                  #
# --------------------------------------------------------------------- #


def test_profile_inverted_range_falls_back_and_flashes_error(db, client):
    seed_user(db)
    login(client)
    response = client.get(
        "/profile?date_from=2026-09-08&date_to=2026-09-01"
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Start date must be before end date." in html, (
        "An inverted date range must flash a user-visible error"
    )
    # Falls back to the unfiltered view.
    assert FULL_TOTAL in html
    for _, _, _, description in EXPENSES:
        assert description in html


# --------------------------------------------------------------------- #
# Malformed date string                                                #
# --------------------------------------------------------------------- #


def test_profile_malformed_date_from_does_not_crash(db, client):
    seed_user(db)
    login(client)
    response = client.get("/profile?date_from=not-a-date&date_to=2026-09-08")
    assert response.status_code == 200, "Malformed date must not produce a 500"
    html = response.get_data(as_text=True)
    # Falls back to unfiltered view since only one bound remained valid.
    assert FULL_TOTAL in html
    for _, _, _, description in EXPENSES:
        assert description in html


def test_profile_malformed_date_to_does_not_crash(db, client):
    seed_user(db)
    login(client)
    response = client.get("/profile?date_from=2026-09-01&date_to=garbage")
    assert response.status_code == 200, "Malformed date must not produce a 500"
    html = response.get_data(as_text=True)
    assert FULL_TOTAL in html


def test_profile_both_dates_malformed_does_not_crash(db, client):
    seed_user(db)
    login(client)
    response = client.get("/profile?date_from=xxxx&date_to=yyyy")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert FULL_TOTAL in html


# --------------------------------------------------------------------- #
# Zero matching expenses in range                                      #
# --------------------------------------------------------------------- #


def test_profile_range_with_no_matches_shows_zero_state(db, client):
    seed_user(db)
    login(client)
    response = client.get(
        "/profile?date_from=2027-01-01&date_to=2027-01-31"
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "0.00" in html, "Total spent should be Rs0.00 when nothing matches"
    assert "0" in html, "Transaction count should be 0 when nothing matches"
    for _, category, _, _ in EXPENSES:
        assert category not in html, (
            f"Category breakdown should be empty, but found {category}"
        )
    for _, _, _, description in EXPENSES:
        assert description not in html


def test_profile_range_with_no_matches_no_server_error(db, client):
    seed_user(db, with_expenses=False)
    login(client)
    response = client.get(
        "/profile?date_from=2027-01-01&date_to=2027-01-31"
    )
    assert response.status_code == 200


# --------------------------------------------------------------------- #
# Currency formatting still applied under filtered views                #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "query_string",
    [
        "",
        "?date_from=2026-09-01&date_to=2026-09-08",
        "?date_from=2027-01-01&date_to=2027-01-31",
        "?date_from=not-a-date&date_to=2026-09-08",
        "?date_from=2026-09-08&date_to=2026-09-01",
    ],
)
def test_profile_currency_symbol_present_under_all_filter_states(db, client, query_string):
    seed_user(db)
    login(client)
    response = client.get(f"/profile{query_string}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "₹" in html, "Currency amounts must always display the Rs symbol"
