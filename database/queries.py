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


def get_summary_stats(user_id):
    """Return {"total_spent", "transaction_count", "top_category"} for user_id.

    total_spent is a comma/2-decimal string (e.g. "9,100.00").
    top_category is "—" when the user has no expenses.
    """
    with closing(get_db()) as db:
        totals_row = db.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
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
            "WHERE user_id = ? GROUP BY category "
            "ORDER BY total DESC, category ASC LIMIT 1",
            (user_id,),
        ).fetchone()

    return {
        "total_spent": "{:,.2f}".format(total),
        "transaction_count": cnt,
        "top_category": top_row["category"],
    }


def get_recent_transactions(user_id, limit=10):
    """Return the user's most recent expenses, newest first, capped at limit.

    Each item is {"date", "description", "category", "amount"} where date is
    formatted like "12 Sep 2026" and amount is a comma/2-decimal string.
    """
    with closing(get_db()) as db:
        rows = db.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    transactions = []
    for row in rows:
        row_date = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append(
            {
                "date": row_date.strftime("%d %b %Y"),
                "description": row["description"],
                "category": row["category"],
                "amount": "{:,.2f}".format(row["amount"]),
            }
        )

    return transactions


def get_category_breakdown(user_id):
    """Return per-category totals for user_id, sorted by amount descending.

    Each item is {"name", "amount", "pct"} where amount is a comma/2-decimal
    string and pct values are ints that sum to exactly 100. Empty list if the
    user has no expenses.
    """
    with closing(get_db()) as db:
        rows = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,),
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
