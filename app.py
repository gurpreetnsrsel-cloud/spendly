import os
import sqlite3
from contextlib import closing

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    def form_error(message):
        return render_template("register.html", error=message, name=name, email=email)

    if not name or not email or not password or not confirm_password:
        return form_error("Please fill in all fields.")

    if len(password) < 8:
        return form_error("Password must be at least 8 characters long.")

    if password != confirm_password:
        return form_error("Passwords do not match.")

    password_hash = generate_password_hash(password)
    with closing(get_db()) as db:
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return form_error("An account with that email already exists.")
        try:
            cursor = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return form_error("An account with that email already exists.")
        user_id = cursor.lastrowid

    session.clear()
    session["user_id"] = user_id
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    def form_error(message):
        return render_template("login.html", error=message, email=email)

    if not email or not password:
        return form_error("Please fill in all fields.")

    with closing(get_db()) as db:
        user = db.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return form_error("Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
