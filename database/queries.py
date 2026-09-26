from contextlib import closing
from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return {"name", "email", "member_since"} for user_id, or None if not found."""
    with closing(get_db()) as db:
        row = db.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    if row is None:
        return None

    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created_at.strftime("%B %Y"),
    }


def _date_filter_sql(date_from, date_to):
    """Return (sql_clause, params) for an optional inclusive date range."""
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (date_from, date_to)
    return "", ()


def get_summary_stats(user_id, date_from=None, date_to=None):
    """Return {"total_spent", "transaction_count", "top_category"} for user_id.

    total_spent is a comma/2-decimal string (e.g. "9,100.00").
    top_category is "—" when the user has no expenses.
    """
    clause, date_params = _date_filter_sql(date_from, date_to)
    with closing(get_db()) as db:
        totals_row = db.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id,) + date_params,
        ).fetchone()

        cnt = totals_row["cnt"]
        total = totals_row["total"]

        if cnt == 0:
            return {
                "total_spent": "0.00",
                "transaction_count": 0,
                "top_category": "—",
            }

        top_row = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC LIMIT 1",
            (user_id,) + date_params,
        ).fetchone()

    return {
        "total_spent": "{:,.2f}".format(total),
        "transaction_count": cnt,
        "top_category": top_row["category"],
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Return the user's most recent expenses, newest first, capped at limit.

    Each item is {"date", "description", "category", "amount"} where date is
    formatted like "12 Sep 2026" and amount is a comma/2-decimal string.
    """
    clause, date_params = _date_filter_sql(date_from, date_to)
    with closing(get_db()) as db:
        rows = db.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id,) + date_params + (limit,),
        ).fetchall()

    transactions = []
    for row in rows:
        row_date = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append(
            {
                "id": row["id"],
                "date": row_date.strftime("%d %b %Y"),
                "description": row["description"],
                "category": row["category"],
                "amount": "{:,.2f}".format(row["amount"]),
            }
        )

    return transactions


def insert_expense(user_id, amount, category, expense_date, description):
    """Insert a new expense row for user_id and return its new id."""
    with closing(get_db()) as db:
        cursor = db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        db.commit()
        return cursor.lastrowid


def get_expense_by_id(expense_id, user_id):
    """Return {"id", "amount", "category", "date", "description"} for the
    given expense_id, scoped to user_id, or None if not found/not owned."""
    with closing(get_db()) as db:
        row = db.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "date": row["date"],
        "description": row["description"],
    }


def update_expense(expense_id, user_id, amount, category, expense_date, description):
    """Update an existing expense row owned by user_id."""
    with closing(get_db()) as db:
        db.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, expense_date, description, expense_id, user_id),
        )
        db.commit()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Return per-category totals for user_id, sorted by amount descending.

    Each item is {"name", "amount", "pct"} where amount is a comma/2-decimal
    string and pct values are ints that sum to exactly 100. Empty list if the
    user has no expenses.
    """
    clause, date_params = _date_filter_sql(date_from, date_to)
    with closing(get_db()) as db:
        rows = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category ORDER BY total DESC",
            (user_id,) + date_params,
        ).fetchall()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)

    breakdown = []
    for row in rows:
        pct = round(100 * row["total"] / grand_total)
        breakdown.append(
            {
                "name": row["category"],
                "amount": "{:,.2f}".format(row["total"]),
                "pct": pct,
            }
        )

    diff = 100 - sum(item["pct"] for item in breakdown)
    breakdown[0]["pct"] += diff

    return breakdown
