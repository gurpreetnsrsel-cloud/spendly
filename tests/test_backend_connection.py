import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"

# 8 expenses across 7 categories, matching the spec's expected totals:
# total_spent = 346.24, transaction_count = 8, top_category = "Bills"
EXPENSES = [
    (49.99, "Food", "2026-09-01", "Groceries"),
    (8.75, "Food", "2026-09-02", "Coffee"),
    (15.50, "Transport", "2026-09-03", "Bus pass"),
    (150.00, "Bills", "2026-09-04", "Electricity bill"),
    (30.00, "Health", "2026-09-05", "Pharmacy"),
    (25.00, "Entertainment", "2026-09-06", "Movie tickets"),
    (57.00, "Shopping", "2026-09-07", "New shoes"),
    (10.00, "Other", "2026-09-08", "Miscellaneous"),
]


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


# --- unit tests: database/queries.py ---


def test_get_user_by_id_valid(db):
    user_id = seed_user(db, with_expenses=False)
    user = get_user_by_id(user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == EMAIL
    assert isinstance(user["member_since"], str) and user["member_since"]


def test_get_user_by_id_missing(db):
    assert get_user_by_id(999) is None


def test_get_summary_stats_with_expenses(db):
    user_id = seed_user(db)
    stats = get_summary_stats(user_id)
    assert stats["total_spent"] == "346.24"
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(db):
    user_id = seed_user(db, with_expenses=False)
    stats = get_summary_stats(user_id)
    assert stats == {"total_spent": "0.00", "transaction_count": 0, "top_category": "—"}


def test_get_recent_transactions_with_expenses(db):
    user_id = seed_user(db)
    transactions = get_recent_transactions(user_id)
    assert len(transactions) == 8
    dates = [t["date"] for t in transactions]
    assert dates == sorted(dates, reverse=True)
    for t in transactions:
        assert set(t.keys()) == {"id", "date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(db):
    user_id = seed_user(db, with_expenses=False)
    assert get_recent_transactions(user_id) == []


def test_get_category_breakdown_with_expenses(db):
    user_id = seed_user(db)
    categories = get_category_breakdown(user_id)
    assert len(categories) == 7
    totals = [float(c["amount"].replace(",", "")) for c in categories]
    assert totals == sorted(totals, reverse=True)
    assert sum(c["pct"] for c in categories) == 100
    assert categories[0]["name"] == "Bills"


def test_get_category_breakdown_no_expenses(db):
    user_id = seed_user(db, with_expenses=False)
    assert get_category_breakdown(user_id) == []


# --- route tests: GET /profile ---


def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_authenticated_shows_real_data(db, client):
    seed_user(db)
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Demo User" in html
    assert EMAIL in html
    assert "₹" in html
    assert "346.24" in html
    assert "Bills" in html

    # newest-first order: most recent expense description appears before the oldest
    assert html.index("Miscellaneous") < html.index("Groceries")
