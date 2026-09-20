import pytest
from werkzeug.security import check_password_hash

import database.db as db_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()

    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def all_users():
    conn = db_module.get_db()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return rows


def register(
    client, name="Test User", email="test@example.com", password="password123", confirm=None
):
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password if confirm is None else confirm,
        },
    )


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create your account" in response.data


def test_valid_registration_creates_hashed_user_and_session(client):
    response = register(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    users = all_users()
    assert len(users) == 1
    assert users[0]["email"] == "test@example.com"
    assert users[0]["password_hash"] != "password123"
    assert check_password_hash(users[0]["password_hash"], "password123")

    with client.session_transaction() as sess:
        assert sess["user_id"] == users[0]["id"]


def test_duplicate_email_rejected_case_insensitively(client):
    register(client, email="a@example.com")
    response = register(client, email="A@Example.com")

    assert response.status_code == 200
    assert b"already exists" in response.data
    assert len(all_users()) == 1


@pytest.mark.parametrize("field", ["name", "email", "password", "confirm_password"])
def test_missing_field_rerenders_with_error(client, field):
    data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "confirm_password": "password123",
    }
    data[field] = ""
    response = client.post("/register", data=data)

    assert response.status_code == 200
    assert b"Please fill in all fields." in response.data
    assert all_users() == []


def test_whitespace_only_name_rejected(client):
    response = register(client, name="   ")
    assert response.status_code == 200
    assert all_users() == []


def test_short_password_rejected_and_eight_chars_accepted(client):
    response = register(client, password="1234567")
    assert response.status_code == 200
    assert b"at least 8 characters" in response.data
    assert all_users() == []

    assert register(client, password="12345678").status_code == 302
    assert len(all_users()) == 1


def test_password_mismatch_rejected(client):
    response = register(client, password="password123", confirm="password124")

    assert response.status_code == 200
    assert b"Passwords do not match." in response.data
    assert all_users() == []


def test_form_has_confirm_password_field(client):
    assert b'name="confirm_password"' in client.get("/register").data


def test_error_rerender_keeps_name_and_email_but_not_password(client):
    response = register(client, name="Ada", email="ada@example.com", password="short")

    assert b'value="Ada"' in response.data
    assert b'value="ada@example.com"' in response.data
    assert b"short" not in response.data.replace(b"Min. 8 characters", b"").replace(
        b"at least 8 characters long", b""
    )


def test_multiple_distinct_users_register(client):
    for i in range(3):
        assert register(client, email=f"user{i}@example.com").status_code == 302

    users = all_users()
    assert len(users) == 3
    assert len({u["id"] for u in users}) == 3
