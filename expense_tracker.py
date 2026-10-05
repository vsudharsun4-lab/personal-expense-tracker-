from collections import defaultdict
from datetime import date
import json
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__)
app.secret_key = "personal-expense-tracker"
DATA_FILE = Path(__file__).with_name("expenses.json")
DEFAULT_BUDGET = 30000.0


def load_data():
    if not DATA_FILE.exists():
        return {"expenses": [], "budget": DEFAULT_BUDGET}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"expenses": [], "budget": DEFAULT_BUDGET}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def current_month():
    return date.today().strftime("%Y-%m")


def month_total(expenses, month):
    return sum(expense["amount"] for expense in expenses if expense["date"].startswith(month))


def dashboard_data(data, selected_month):
    expenses = data["expenses"]
    filtered = [expense for expense in expenses if expense["date"].startswith(selected_month)]
    categories = defaultdict(float)
    for expense in filtered:
        categories[expense["category"]] += expense["amount"]
    highest = max(filtered, key=lambda expense: expense["amount"], default=None)
    total = sum(categories.values())
    budget = data.get("budget", DEFAULT_BUDGET)
    return {
        "expenses": filtered,
        "total": total,
        "count": len(filtered),
        "highest": highest,
        "categories": dict(sorted(categories.items())),
        "budget": budget,
        "budget_remaining": budget - total,
        "budget_warning": total > budget,
    }


@app.route("/", methods=["GET", "POST"])
def dashboard():
    data = load_data()
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        amount_text = request.form.get("amount", "")
        expense_date = request.form.get("date", date.today().isoformat())
        try:
            amount = float(amount_text)
        except ValueError:
            amount = 0
        if not category or amount <= 0 or not expense_date:
            flash("Enter a category and an amount greater than zero.", "error")
        else:
            next_id = max((expense["id"] for expense in data["expenses"]), default=0) + 1
            data["expenses"].append({
                "id": next_id, "category": category, "amount": amount, "date": expense_date
            })
            save_data(data)
            flash("Expense added.", "success")
        return redirect(url_for("dashboard", month=expense_date[:7]))

    selected_month = request.args.get("month", current_month())
    search = request.args.get("search", "").strip().lower()
    view = dashboard_data(data, selected_month)
    if search:
        view["expenses"] = [expense for expense in view["expenses"] if search in expense["category"].lower()]
    return render_template("dashboard.html", **view, selected_month=selected_month, search=search)


@app.post("/delete/<int:expense_id>")
def delete_expense(expense_id):
    data = load_data()
    data["expenses"] = [expense for expense in data["expenses"] if expense["id"] != expense_id]
    save_data(data)
    flash("Expense deleted.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    data = load_data()
    expense = next((item for item in data["expenses"] if item["id"] == expense_id), None)
    if expense is None:
        flash("Expense not found.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        expense["category"] = request.form["category"].strip()
        expense["amount"] = float(request.form["amount"])
        expense["date"] = request.form["date"]
        save_data(data)
        flash("Expense updated.", "success")
        return redirect(url_for("dashboard", month=expense["date"][:7]))
    return render_template("edit.html", expense=expense)


@app.post("/budget")
def set_budget():
    data = load_data()
    try:
        budget = float(request.form["budget"])
        if budget <= 0:
            raise ValueError
        data["budget"] = budget
        save_data(data)
        flash("Monthly budget updated.", "success")
    except (KeyError, ValueError):
        flash("Budget must be greater than zero.", "error")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)