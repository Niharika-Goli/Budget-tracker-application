from flask import (
    Flask,
    render_template,
    request,
    url_for,
    flash,
    redirect,
    Response
)

from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, date as dt_date
from sqlalchemy import func

app = Flask(__name__)

# CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my-secret-key'

db = SQLAlchemy(app)


# MODEL
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.String(120), nullable=False)

    Amount = db.Column(db.Float, nullable=False)

    Category = db.Column(db.String(120), nullable=False)

    Date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )


# CREATE DATABASE
with app.app_context():
    db.create_all()


# CATEGORIES
CATEGORIES = [
    'Food',
    'Transport',
    'Rent',
    'Utilities',
    'Health',
    'EMI',
    'Gold/Silver'
]


# HELPER FUNCTION
def parse_date_or_none(s: str):

    if not s:
        return None

    try:
        return datetime.strptime(
            s,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        return None


# HOME PAGE
@app.route("/")
def index():

    # FILTER VALUES
    start_str = (request.args.get("start") or "").strip()

    end_str = (request.args.get("end") or "").strip()

    selected_category = (
        request.args.get("Category") or ""
    ).strip()

    # CONVERT TO DATE
    start_date = parse_date_or_none(start_str)

    end_date = parse_date_or_none(end_str)

    # VALIDATION
    if (
        start_date and
        end_date and
        end_date < start_date
    ):

        flash(
            "End date cannot be before start date",
            "error"
        )

        start_date = None
        end_date = None

        start_str = ""
        end_str = ""

    # MAIN QUERY
    q = Expense.query

    if start_date:
        q = q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        q = q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        q = q.filter(
            Expense.Category == selected_category
        )

    expenses = q.order_by(
        Expense.Date.desc(),
        Expense.id.desc()
    ).all()

    # TOTAL
    total = round(
        sum(e.Amount for e in expenses),
        2
    )

    # PIE CHART
    cat_q = db.session.query(
        Expense.Category,
        func.sum(Expense.Amount)
    )

    if start_date:
        cat_q = cat_q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        cat_q = cat_q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        cat_q = cat_q.filter(
            Expense.Category == selected_category
        )

    cat_rows = cat_q.group_by(
        Expense.Category
    ).all()

    cat_labels = [c for c, _ in cat_rows]

    cat_values = [
        round(float(s or 0), 2)
        for _, s in cat_rows
    ]

    # DAY CHART
    day_q = db.session.query(
        Expense.Date,
        func.sum(Expense.Amount)
    )

    if start_date:
        day_q = day_q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        day_q = day_q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        day_q = day_q.filter(
            Expense.Category == selected_category
        )

    day_rows = day_q.group_by(
        Expense.Date
    ).order_by(
        Expense.Date
    ).all()

    day_labels = [
        d.isoformat()
        for d, _ in day_rows
    ]

    day_values = [
        round(float(s or 0), 2)
        for _, s in day_rows
    ]

    return render_template(
        "index.html",

        categories=CATEGORIES,

        today=date.today().isoformat(),

        expenses=expenses,

        total=total,

        start_str=start_str,

        end_str=end_str,

        selected_category=selected_category,

        cat_labels=cat_labels,

        cat_values=cat_values,

        day_labels=day_labels,

        day_values=day_values
    )


# ADD EXPENSE
@app.route("/add", methods=['POST'])
def add():

    description = (
        request.form.get("description") or ""
    ).strip()

    Amount_str = (
        request.form.get("Amount") or ""
    ).strip()

    Category = (
        request.form.get("Category") or ""
    ).strip()

    date_str = (
        request.form.get("date") or ""
    ).strip()

    # VALIDATION
    if (
        not description or
        not Amount_str or
        not Category
    ):

        flash(
            "Please fill all fields",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # AMOUNT VALIDATION
    try:

        Amount = float(Amount_str)

        if Amount <= 0:
            raise ValueError

    except ValueError:

        flash(
            "Amount must be positive number",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # DATE VALIDATION
    try:

        d = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

            if date_str
            else date.today()
        )

    except ValueError:

        d = date.today()

    # SAVE
    e = Expense(
        description=description,
        Amount=Amount,
        Category=Category,
        Date=d
    )

    db.session.add(e)

    db.session.commit()

    flash(
        "Expense added successfully",
        "success"
    )

    return redirect(
        url_for("index")
    )


# DELETE
@app.route(
    '/delete/<int:expense_id>',
    methods=['POST']
)
def delete(expense_id):

    e = Expense.query.get_or_404(
        expense_id
    )

    db.session.delete(e)

    db.session.commit()

    flash(
        "Expense deleted",
        "success"
    )

    return redirect(
        url_for("index")
    )

@app.route('/edit/<int:expense_id>',methods=['GET'])
def edit(expense_id):
    e = Expense.query.get_or_404(expense_id)
    return render_template("edit.html",expense=e, categories=CATEGORIES, tday=dt_date.today().isoformat())


@app.route('/edit/<int:expense_id>',methods=['POST'])
def edit_post(expense_id):

    e = Expense.query.get_or_404(expense_id)

    description = (request.form.get("description") or "").strip()
    Amount_str = (request.form.get("Amount") or "").strip()
    Category = (request.form.get("Category") or "").strip()
    date_str = (request.form.get("Date") or "").strip()

    if not description or not Amount_str or not Category:
        flash("Please fill description, Amount, Category", "error")
        return redirect(url_for("edit", expense_id=expense_id))

    try:
        Amount = float(Amount_str)

        if Amount <= 0:
            raise ValueError

    except ValueError:
        flash("Amount must be a positive number", "error")
        return redirect(url_for("edit", expense_id=expense_id))

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else dt_date.today()

    except ValueError:
        d = dt_date.today()

    e.description = description
    e.Amount = Amount
    e.Category = Category
    e.Date = d

    db.session.commit()

    flash("Expense Updated", "success")

    return redirect(url_for("index"))




# EXPORT CSV
@app.route("/export.csv")
def export_csv():

    start_str = (
        request.args.get("start") or ""
    ).strip()

    end_str = (
        request.args.get("end") or ""
    ).strip()

    selected_category = (
        request.args.get("Category") or ""
    ).strip()

    start_date = parse_date_or_none(
        start_str
    )

    end_date = parse_date_or_none(
        end_str
    )

    q = Expense.query

    if start_date:
        q = q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        q = q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        q = q.filter(
            Expense.Category == selected_category
        )

    expenses = q.order_by(
        Expense.Date,
        Expense.id
    ).all()

    # CSV CONTENT
    lines = [
        "Date,Description,Category,Amount"
    ]

    for e in expenses:

        lines.append(
            f"{e.Date.isoformat()},"
            f"{e.description},"
            f"{e.Category},"
            f"{e.Amount:.2f}"
        )

    csv_data = "\n".join(lines)

    # FILE NAME
    fname_start = start_str or "all"

    fname_end = end_str or "all"

    filename = (
        f"expenses_{fname_start}"
        f"_to_{fname_end}.csv"
    )

    return Response(
        csv_data,

        headers={
            "Content-Type": "text/csv",

            "Content-Disposition":
            f"attachment; filename={filename}"
        }
    )


# RUN APP
if __name__ == "__main__":
    app.run(
        debug=True,
        port=4848
    )