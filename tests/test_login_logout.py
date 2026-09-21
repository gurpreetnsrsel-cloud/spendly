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
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", EMAIL, generate_password_hash(PASSWORD)),
    )
    conn.commit()
    conn.close()

    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def session_user_id(client):
    with client.session_transaction() as sess:
        return sess.get("user_id")


def test_get_login_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_valid_login_sets_session_and_redirects(client):
    response = login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert session_user_id(client) is not None


def test_email_is_case_and_whitespace_insensitive(client):
    response = login(client, email="  TEST@Example.COM ")

    assert response.status_code == 302
    assert session_user_id(client) is not None


@pytest.mark.parametrize(
    "email, password",
    [(EMAIL, "wrongpassword"), ("nobody@example.com", PASSWORD)],
)
def test_bad_credentials_show_generic_error(client, email, password):
    response = login(client, email=email, password=password)

    assert response.status_code == 200
    assert b"Invalid email or password." in response.data
    assert session_user_id(client) is None


@pytest.mark.parametrize("email, password", [("", PASSWORD), (EMAIL, "")])
def test_missing_field_shows_error(client, email, password):
    response = login(client, email=email, password=password)

    assert response.status_code == 200
    assert b"Please fill in all fields." in response.data
    assert session_user_id(client) is None


def test_failed_login_repopulates_email_but_not_password(client):
    response = login(client, password="wrongpassword")

    assert EMAIL.encode() in response.data
    assert b"wrongpassword" not in response.data


def test_login_page_redirects_when_logged_in(client):
    login(client)
    response = client.get("/login")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_logout_clears_session_and_redirects_home(client):
    login(client)
    response = client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert session_user_id(client) is None


def test_logout_when_logged_out_still_redirects(client):
    response = client.get("/logout")

    assert response.status_code == 302


def test_navbar_reflects_auth_state(client):
    logged_out = client.get("/").data
    assert b"Sign in" in logged_out
    assert b"Get started" in logged_out
    assert b"Sign out" not in logged_out

    login(client)
    logged_in = client.get("/").data
    assert b"Sign out" in logged_in
    assert b"Get started" not in logged_in


def test_register_page_redirects_when_logged_in(client):
    login(client)

    get_response = client.get("/register")
    post_response = client.post("/register", data={"email": "x@example.com"})

    for response in (get_response, post_response):
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
