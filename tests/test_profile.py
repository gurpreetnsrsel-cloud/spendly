import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module

EMAIL = "test@example.com"
PASSWORD = "password123"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()

    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", EMAIL, generate_password_hash(PASSWORD)),
    )
    user_id = cursor.lastrowid
    for amount, category, expense_date, description in [
        (49.99, "Food", "2026-09-01", "Groceries"),
        (15.50, "Transport", "2026-09-03", "Bus pass"),
        (120.00, "Bills", "2026-09-05", "Electricity bill"),
    ]:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
    conn.commit()
    conn.close()

    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def login(client):
    return client.post("/login", data={"email": EMAIL, "password": PASSWORD})


def test_profile_redirects_to_login_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(client):
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Total spent" in html
    assert "Transaction history" in html
    assert "Category breakdown" in html
    assert html.count("<tr>") >= 4  # header + at least three rows
    assert "Sign out" in html


def test_profile_template_has_no_hex_or_inline_styles():
    with open("templates/profile.html", encoding="utf-8") as f:
        source = f.read()
    assert "style=" not in source
    import re

    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source)
