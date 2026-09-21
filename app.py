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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded demo data — real queries are wired up in Step 5.
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }
    stats = {
        "total_spent": "9,100.00",
        "transaction_count": 7,
        "top_category": "Food",
    }
    transactions = [
        {"date": "12 Sep 2026", "description": "Groceries", "category": "Food", "amount": "1,850.00"},
        {"date": "10 Sep 2026", "description": "Metro card recharge", "category": "Transport", "amount": "500.00"},
        {"date": "08 Sep 2026", "description": "Electricity bill", "category": "Bills", "amount": "2,400.00"},
        {"date": "06 Sep 2026", "description": "Pharmacy", "category": "Health", "amount": "640.00"},
        {"date": "04 Sep 2026", "description": "Movie tickets", "category": "Entertainment", "amount": "900.00"},
        {"date": "02 Sep 2026", "description": "New shoes", "category": "Shopping", "amount": "2,100.00"},
        {"date": "01 Sep 2026", "description": "Lunch with friends", "category": "Food", "amount": "710.00"},
    ]
    # bar_width is relative to the largest category, in steps of 10 (CSS class).
    categories = [
        {"name": "Food", "total": "2,560.00", "percent": 28, "bar_width": 100},
        {"name": "Bills", "total": "2,400.00", "percent": 26, "bar_width": 90},
        {"name": "Shopping", "total": "2,100.00", "percent": 23, "bar_width": 80},
        {"name": "Entertainment", "total": "900.00", "percent": 10, "bar_width": 40},
        {"name": "Health", "total": "640.00", "percent": 7, "bar_width": 30},
        {"name": "Transport", "total": "500.00", "percent": 5, "bar_width": 20},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

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
