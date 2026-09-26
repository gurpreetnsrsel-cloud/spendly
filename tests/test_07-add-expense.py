"""Tests for the Step 7 "Add Expense" feature.

Derived strictly from .claude/specs/07-add-expense.md — routes, validation
rules, and definition-of-done checklist. Assertions avoid coupling to
implementation-specific copy (exact error wording) and instead check the
spec-mandated *behaviors*: auth redirects, form fields present, values
preserved on error, no DB row created on invalid input, and a DB row
created (visible on /profile) on valid input.
"""
import re

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from database.db import CATEGORIES

EMAIL = "addexpense@example.com"
PASSWORD = "password123"
OTHER_EMAIL = "other@example.com"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()

    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Add Expense User", EMAIL, generate_password_hash(PASSWORD)),
    )
    user_id = cursor.lastrowid

    other_cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", OTHER_EMAIL, generate_password_hash(PASSWORD)),
    )
    other_user_id = other_cursor.lastrowid

    conn.commit()
    conn.close()

    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        client.user_id = user_id
        client.other_user_id = other_user_id
        yield client


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def expenses_for(user_id):
    conn = db_module.get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def expense_count(user_id=None):
    conn = db_module.get_db()
    if user_id is None:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
    conn.close()
    return row["cnt"]


VALID_CATEGORY = CATEGORIES[0]


# --------------------------------------------------------------------- #
# Auth guard — DoD: "Visiting /expenses/add while logged out redirects  #
# to /login"                                                             #
# --------------------------------------------------------------------- #

class TestAuthGuard:
    def test_get_redirects_to_login_when_logged_out(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_post_redirects_to_login_when_logged_out(self, client):
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_post_when_logged_out_does_not_insert_a_row(self, client):
        before = expense_count()
        client.post(
            "/expenses/add",
            data={"amount": "10", "category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        assert expense_count() == before


# --------------------------------------------------------------------- #
# GET form — DoD: "Visiting /expenses/add while logged in shows a form  #
# with amount, category, date, and description fields"                  #
# --------------------------------------------------------------------- #

class TestRenderForm:
    def test_get_renders_form_when_logged_in(self, client):
        login(client)
        response = client.get("/expenses/add")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'name="amount"' in html
        assert 'name="category"' in html
        assert 'name="date"' in html
        assert 'name="description"' in html

    def test_category_options_come_from_database_categories(self, client):
        login(client)
        html = client.get("/expenses/add").get_data(as_text=True)
        for category in CATEGORIES:
            assert category in html, f"Expected category {category!r} option in form"

    def test_get_form_extends_base_layout(self, client):
        login(client)
        html = client.get("/expenses/add").get_data(as_text=True)
        # base.html landmarks: nav present on every page per project conventions
        assert "<nav" in html or "navbar" in html.lower()

    def test_currency_is_rupee_not_dollar_or_pound(self, client):
        login(client)
        html = client.get("/expenses/add").get_data(as_text=True)
        assert "₹" in html, "Expected the rupee sign somewhere on the form"
        assert "$" not in html
        assert "£" not in html


# --------------------------------------------------------------------- #
# Happy path — DoD: valid submission inserts a row scoped to the        #
# current user and redirects to /profile; new expense appears in the    #
# profile transaction list, summary stats, and category breakdown       #
# --------------------------------------------------------------------- #

class TestValidSubmission:
    def test_valid_submission_redirects_to_profile(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={
                "amount": "42.50",
                "category": VALID_CATEGORY,
                "date": "2026-09-15",
                "description": "New shoes",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

    def test_valid_submission_inserts_row_for_current_user(self, client):
        login(client)
        before = expense_count(client.user_id)
        client.post(
            "/expenses/add",
            data={
                "amount": "42.50",
                "category": VALID_CATEGORY,
                "date": "2026-09-15",
                "description": "New shoes",
            },
        )
        assert expense_count(client.user_id) == before + 1

        rows = expenses_for(client.user_id)
        assert any(
            r["description"] == "New shoes"
            and r["category"] == VALID_CATEGORY
            and r["date"] == "2026-09-15"
            and abs(r["amount"] - 42.50) < 1e-6
            for r in rows
        ), "Expected the newly submitted expense to be present with the submitted values"

    def test_valid_submission_does_not_insert_for_other_user(self, client):
        login(client)
        before_other = expense_count(client.other_user_id)
        client.post(
            "/expenses/add",
            data={
                "amount": "10",
                "category": VALID_CATEGORY,
                "date": "2026-09-15",
                "description": "Mine only",
            },
        )
        assert expense_count(client.other_user_id) == before_other

    def test_new_expense_appears_on_profile_transaction_list(self, client):
        login(client)
        client.post(
            "/expenses/add",
            data={
                "amount": "42.50",
                "category": VALID_CATEGORY,
                "date": "2026-09-15",
                "description": "New shoes",
            },
        )
        profile_html = client.get("/profile").get_data(as_text=True)
        assert "New shoes" in profile_html
        assert "42.50" in profile_html

    def test_new_expense_reflected_in_summary_stats(self, client):
        login(client)
        before_html = client.get("/profile").get_data(as_text=True)
        client.post(
            "/expenses/add",
            data={
                "amount": "500.00",
                "category": VALID_CATEGORY,
                "date": "2026-09-15",
                "description": "Big purchase",
            },
        )
        after_html = client.get("/profile").get_data(as_text=True)
        assert after_html != before_html
        assert "500.00" in after_html

    def test_description_is_optional(self, client):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={
                "amount": "10",
                "category": VALID_CATEGORY,
                "date": "2026-09-16",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
        assert expense_count(client.user_id) == before + 1


# --------------------------------------------------------------------- #
# Amount validation — DoD: missing/zero/negative amount re-shows the    #
# form with an error and no row is inserted                             #
# --------------------------------------------------------------------- #

class TestAmountValidation:
    @pytest.mark.parametrize(
        "amount_value",
        ["", "0", "-5", "not-a-number", "abc", "-0.01", "nan", "inf", "-inf"],
    )
    def test_invalid_amount_reshows_form_without_inserting(self, client, amount_value):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={"amount": amount_value, "category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        assert response.status_code == 200
        assert expense_count(client.user_id) == before

    def test_invalid_amount_shows_an_error_message(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"amount": "0", "category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        html = response.get_data(as_text=True)
        assert "auth-error" in html or "error" in html.lower()

    def test_invalid_amount_preserves_entered_category_and_date(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"amount": "not-a-number", "category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        html = response.get_data(as_text=True)
        assert "2026-09-10" in html
        assert VALID_CATEGORY in html

    def test_missing_amount_field_entirely_does_not_error_500(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"category": VALID_CATEGORY, "date": "2026-09-10"},
        )
        assert response.status_code in (200, 302, 400)
        assert response.status_code != 500


# --------------------------------------------------------------------- #
# Category validation — DoD: category not in CATEGORIES re-shows the    #
# form with an error and no row is inserted                             #
# --------------------------------------------------------------------- #

class TestCategoryValidation:
    def test_unknown_category_reshows_form_without_inserting(self, client):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": "NotARealCategory", "date": "2026-09-10"},
        )
        assert response.status_code == 200
        assert expense_count(client.user_id) == before

    def test_missing_category_reshows_form_without_inserting(self, client):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": "", "date": "2026-09-10"},
        )
        assert response.status_code == 200
        assert expense_count(client.user_id) == before

    def test_unknown_category_shows_an_error_message(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": "NotARealCategory", "date": "2026-09-10"},
        )
        html = response.get_data(as_text=True)
        assert "auth-error" in html or "error" in html.lower()

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_every_documented_category_is_accepted(self, client, category):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={"amount": "5", "category": category, "date": "2026-09-10"},
        )
        assert response.status_code == 302
        assert expense_count(client.user_id) == before + 1


# --------------------------------------------------------------------- #
# Date validation — DoD: invalid or missing date re-shows the form with #
# an error and no row is inserted                                       #
# --------------------------------------------------------------------- #

class TestDateValidation:
    @pytest.mark.parametrize(
        "date_value",
        ["", "not-a-date", "2026-13-40", "15/09/2026", "2026/09/15"],
    )
    def test_invalid_date_reshows_form_without_inserting(self, client, date_value):
        login(client)
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": VALID_CATEGORY, "date": date_value},
        )
        assert response.status_code == 200
        assert expense_count(client.user_id) == before

    def test_invalid_date_shows_an_error_message(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": VALID_CATEGORY, "date": "not-a-date"},
        )
        html = response.get_data(as_text=True)
        assert "auth-error" in html or "error" in html.lower()

    def test_valid_iso_date_is_accepted(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={"amount": "10", "category": VALID_CATEGORY, "date": "2026-01-01"},
        )
        assert response.status_code == 302


# --------------------------------------------------------------------- #
# Input preservation on validation error — spec: "re-render               #
# add_expense.html with the entered values preserved ... never lose      #
# user input"                                                             #
# --------------------------------------------------------------------- #

class TestInputPreservedOnError:
    def test_amount_and_description_preserved_on_bad_category(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={
                "amount": "77.25",
                "category": "BogusCategory",
                "date": "2026-09-10",
                "description": "Keep me around",
            },
        )
        html = response.get_data(as_text=True)
        assert "77.25" in html
        assert "Keep me around" in html

    def test_description_and_category_preserved_on_bad_amount(self, client):
        login(client)
        response = client.post(
            "/expenses/add",
            data={
                "amount": "-1",
                "category": VALID_CATEGORY,
                "date": "2026-09-10",
                "description": "Do not disappear",
            },
        )
        html = response.get_data(as_text=True)
        assert "Do not disappear" in html
        assert VALID_CATEGORY in html


# --------------------------------------------------------------------- #
# Profile entry point — DoD: profile page has a visible "Add Expense"    #
# link that navigates to /expenses/add                                   #
# --------------------------------------------------------------------- #

class TestProfileEntryPoint:
    def test_profile_page_links_to_add_expense(self, client):
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        assert "/expenses/add" in html


# --------------------------------------------------------------------- #
# Implementation rules — spec: raw sqlite3 via get_db(), no ORM, no       #
# inline styles, no hardcoded hex colors, extends base.html               #
# --------------------------------------------------------------------- #

class TestImplementationRules:
    def test_add_expense_template_has_no_hex_colors_or_inline_styles(self):
        with open("templates/add_expense.html", encoding="utf-8") as f:
            source = f.read()
        assert "style=" not in source
        assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source)

    def test_add_expense_template_extends_base(self):
        with open("templates/add_expense.html", encoding="utf-8") as f:
            source = f.read()
        assert '{% extends "base.html" %}' in source or "{% extends 'base.html' %}" in source

    def test_sql_injection_attempt_in_description_is_stored_safely_not_executed(self, client):
        login(client)
        malicious = "'); DROP TABLE expenses; --"
        before = expense_count(client.user_id)
        response = client.post(
            "/expenses/add",
            data={
                "amount": "5",
                "category": VALID_CATEGORY,
                "date": "2026-09-10",
                "description": malicious,
            },
        )
        assert response.status_code == 302
        # expenses table must still exist and contain the new row untouched
        assert expense_count(client.user_id) == before + 1
        rows = expenses_for(client.user_id)
        assert any(r["description"] == malicious for r in rows)
