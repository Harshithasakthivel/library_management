from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import date, datetime, timedelta


# =========================================================
# APPLICATION SETTINGS
# =========================================================

app = Flask(__name__)

app.secret_key = "library_management_system_secret_key"

DATABASE = "library.db"

FINE_PER_DAY = 5


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    conn = sqlite3.connect(
        DATABASE,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA busy_timeout = 30000"
    )

    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db_connection()

    try:

        # =====================================================
        # BOOKS TABLE
        # =====================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,

                author TEXT NOT NULL,

                category TEXT NOT NULL
                    DEFAULT 'General',

                quantity INTEGER NOT NULL
                    DEFAULT 1,

                available_quantity INTEGER NOT NULL
                    DEFAULT 1,

                status TEXT NOT NULL
                    DEFAULT 'Available'
            )
        """)


        # =====================================================
        # STUDENTS TABLE
        # =====================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                department TEXT NOT NULL,

                email TEXT NOT NULL
            )
        """)


        # =====================================================
        # TRANSACTIONS TABLE
        # =====================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                book_id INTEGER NOT NULL,

                student_id INTEGER NOT NULL,

                issue_date TEXT NOT NULL,

                due_date TEXT NOT NULL,

                return_date TEXT,

                fine INTEGER DEFAULT 0,

                status TEXT NOT NULL
                    DEFAULT 'Issued'
            )
        """)


        conn.commit()


    finally:

        conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if username == "admin" and password == "admin123":

            session.clear()

            session["username"] = username

            flash(
                "Login successful! Welcome to the library.",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid username or password.",
            "danger"
        )


    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # TOTAL BOOK COPIES
        # =====================================================

        total_books = conn.execute("""
            SELECT
                COALESCE(SUM(quantity), 0)

            FROM books
        """).fetchone()[0]


        # =====================================================
        # AVAILABLE COPIES
        # =====================================================

        available_books = conn.execute("""
            SELECT
                COALESCE(SUM(available_quantity), 0)

            FROM books
        """).fetchone()[0]


        # =====================================================
        # ISSUED COPIES
        # =====================================================

        issued_books = (
            total_books -
            available_books
        )


        # =====================================================
        # TOTAL STUDENTS
        # =====================================================

        total_students = conn.execute("""
            SELECT COUNT(*)

            FROM students
        """).fetchone()[0]


        # =====================================================
        # OVERDUE TRANSACTIONS
        # =====================================================

        today = date.today()

        overdue_rows = conn.execute("""
            SELECT

                transactions.id,

                transactions.issue_date,

                transactions.due_date,

                books.title,

                students.name

            FROM transactions

            JOIN books
            ON transactions.book_id = books.id

            JOIN students
            ON transactions.student_id = students.id

            WHERE transactions.status = 'Issued'

            AND transactions.due_date < ?

            ORDER BY transactions.due_date ASC

        """, (
            today.isoformat(),
        )).fetchall()


        overdue_books = []

        overdue_total = 0


        for row in overdue_rows:

            due_date = datetime.strptime(
                row["due_date"],
                "%Y-%m-%d"
            ).date()


            late_days = (
                today - due_date
            ).days


            if late_days < 0:

                late_days = 0


            fine = (
                late_days *
                FINE_PER_DAY
            )


            overdue_total += fine


            overdue_books.append({

                "id":
                    row["id"],

                "title":
                    row["title"],

                "name":
                    row["name"],

                "issue_date":
                    row["issue_date"],

                "due_date":
                    row["due_date"],

                "late_days":
                    late_days,

                "fine":
                    fine
            })


        # =====================================================
        # RENDER DASHBOARD
        # =====================================================

        return render_template(

            "dashboard.html",

            total_books=
                total_books,

            available_books=
                available_books,

            issued_books=
                issued_books,

            total_students=
                total_students,

            overdue_books=
                overdue_books,

            overdue_total=
                overdue_total
        )


    finally:

        conn.close()


# =========================================================
# BOOK MANAGEMENT
# =========================================================

@app.route(
    "/books",
    methods=["GET", "POST"]
)
def books():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # ADD BOOK
        # =====================================================

        if request.method == "POST":

            title = request.form.get(
                "title",
                ""
            ).strip()


            author = request.form.get(
                "author",
                ""
            ).strip()


            category = request.form.get(
                "category",
                ""
            ).strip()


            quantity_text = request.form.get(
                "quantity",
                ""
            ).strip()


            if not title:

                flash(
                    "Please enter book title.",
                    "danger"
                )

                return redirect(
                    url_for("books")
                )


            if not author:

                flash(
                    "Please enter author name.",
                    "danger"
                )

                return redirect(
                    url_for("books")
                )


            if not category:

                category = "General"


            try:

                quantity = int(
                    quantity_text
                )

            except ValueError:

                flash(
                    "Quantity must be a number.",
                    "danger"
                )

                return redirect(
                    url_for("books")
                )


            if quantity < 1:

                flash(
                    "Quantity must be at least 1.",
                    "danger"
                )

                return redirect(
                    url_for("books")
                )


            # =================================================
            # INSERT BOOK
            # =================================================

            conn.execute("""
                INSERT INTO books
                (
                    title,
                    author,
                    category,
                    quantity,
                    available_quantity,
                    status
                )

                VALUES
                (?, ?, ?, ?, ?, ?)

            """, (

                title,

                author,

                category,

                quantity,

                quantity,

                "Available"
            ))


            conn.commit()


            flash(
                "Book added successfully!",
                "success"
            )


            return redirect(
                url_for("books")
            )


        # =====================================================
        # SEARCH
        # =====================================================

        search = request.args.get(
            "search",
            ""
        ).strip()


        if search:

            book_list = conn.execute("""
                SELECT *

                FROM books

                WHERE title LIKE ?

                OR author LIKE ?

                OR category LIKE ?

                ORDER BY id DESC

            """, (

                "%" + search + "%",

                "%" + search + "%",

                "%" + search + "%"
            )).fetchall()


        else:

            book_list = conn.execute("""
                SELECT *

                FROM books

                ORDER BY id DESC

            """).fetchall()


        return render_template(

            "books.html",

            books=
                book_list,

            search=
                search
        )


    finally:

        conn.close()


# =========================================================
# DELETE BOOK
# =========================================================

@app.route(
    "/delete_book/<int:book_id>",
    methods=["POST"]
)
def delete_book(book_id):

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    conn = get_db_connection()

    try:

        active_transaction = conn.execute("""
            SELECT id

            FROM transactions

            WHERE book_id = ?

            AND status = 'Issued'

            LIMIT 1

        """, (
            book_id,
        )).fetchone()


        if active_transaction:

            flash(
                "This book cannot be deleted because it is currently issued.",
                "danger"
            )

            return redirect(
                url_for("books")
            )


        conn.execute("""
            DELETE FROM books

            WHERE id = ?

        """, (
            book_id,
        ))


        conn.commit()


        flash(
            "Book deleted successfully!",
            "success"
        )


        return redirect(
            url_for("books")
        )


    finally:

        conn.close()


# =========================================================
# STUDENT MANAGEMENT
# =========================================================

@app.route(
    "/students",
    methods=["GET", "POST"]
)
def students():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # ADD STUDENT
        # =====================================================

        if request.method == "POST":

            name = request.form.get(
                "name",
                ""
            ).strip()


            department = request.form.get(
                "department",
                ""
            ).strip()


            email = request.form.get(
                "email",
                ""
            ).strip()


            if not name:

                flash(
                    "Please enter student name.",
                    "danger"
                )

                return redirect(
                    url_for("students")
                )


            if not department:

                flash(
                    "Please enter department.",
                    "danger"
                )

                return redirect(
                    url_for("students")
                )


            if not email:

                flash(
                    "Please enter email.",
                    "danger"
                )

                return redirect(
                    url_for("students")
                )


            conn.execute("""
                INSERT INTO students
                (
                    name,
                    department,
                    email
                )

                VALUES
                (?, ?, ?)

            """, (

                name,

                department,

                email
            ))


            conn.commit()


            flash(
                "Student added successfully!",
                "success"
            )


            return redirect(
                url_for("students")
            )


        # =====================================================
        # GET STUDENTS
        # =====================================================

        student_list = conn.execute("""
            SELECT *

            FROM students

            ORDER BY id DESC

        """).fetchall()


        return render_template(

            "students.html",

            students=
                student_list
        )


    finally:

        conn.close()


# =========================================================
# ISSUE AND RETURN PAGE
# =========================================================

@app.route("/issue-return")
def issue_return():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # AVAILABLE BOOKS
        # =====================================================

        available_books = conn.execute("""
            SELECT *

            FROM books

            WHERE available_quantity > 0

            ORDER BY title ASC

        """).fetchall()


        # =====================================================
        # STUDENTS
        # =====================================================

        student_list = conn.execute("""
            SELECT *

            FROM students

            ORDER BY name ASC

        """).fetchall()


        # =====================================================
        # CURRENTLY ISSUED
        # =====================================================

        issued_transactions = conn.execute("""
            SELECT

                transactions.*,

                books.title,

                books.author,

                students.name,

                students.department

            FROM transactions

            JOIN books
            ON transactions.book_id = books.id

            JOIN students
            ON transactions.student_id = students.id

            WHERE transactions.status = 'Issued'

            ORDER BY transactions.id DESC

        """).fetchall()


        # =====================================================
        # TRANSACTION HISTORY
        # =====================================================

        history = conn.execute("""
            SELECT

                transactions.*,

                books.title,

                books.author,

                students.name,

                students.department

            FROM transactions

            JOIN books
            ON transactions.book_id = books.id

            JOIN students
            ON transactions.student_id = students.id

            ORDER BY transactions.id DESC

        """).fetchall()


        return render_template(

            "issue_return.html",

            available_books=
                available_books,

            students=
                student_list,

            issued_transactions=
                issued_transactions,

            history=
                history
        )


    finally:

        conn.close()


# =========================================================
# ISSUE BOOK
# =========================================================

@app.route(
    "/issue_book",
    methods=["POST"]
)
def issue_book():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    book_id = request.form.get(
        "book_id"
    )


    student_id = request.form.get(
        "student_id"
    )


    issue_date = request.form.get(
        "issue_date"
    )


    due_date = request.form.get(
        "due_date"
    )


    if not book_id:

        flash(
            "Please select a book.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    if not student_id:

        flash(
            "Please select a student.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    if not issue_date or not due_date:

        flash(
            "Please select issue date and due date.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    try:

        issue_date_obj = datetime.strptime(
            issue_date,
            "%Y-%m-%d"
        ).date()


        due_date_obj = datetime.strptime(
            due_date,
            "%Y-%m-%d"
        ).date()


    except ValueError:

        flash(
            "Invalid date.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    if due_date_obj < issue_date_obj:

        flash(
            "Due date cannot be before issue date.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # CHECK BOOK
        # =====================================================

        book = conn.execute("""
            SELECT *

            FROM books

            WHERE id = ?

        """, (
            book_id,
        )).fetchone()


        if not book:

            flash(
                "Book not found.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        if book["available_quantity"] <= 0:

            flash(
                "This book is currently unavailable.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        # =====================================================
        # CHECK STUDENT
        # =====================================================

        student = conn.execute("""
            SELECT *

            FROM students

            WHERE id = ?

        """, (
            student_id,
        )).fetchone()


        if not student:

            flash(
                "Student not found.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        # =====================================================
        # ADD TRANSACTION
        # =====================================================

        conn.execute("""
            INSERT INTO transactions
            (
                book_id,
                student_id,
                issue_date,
                due_date,
                return_date,
                fine,
                status
            )

            VALUES
            (?, ?, ?, ?, ?, ?, ?)

        """, (

            book_id,

            student_id,

            issue_date,

            due_date,

            None,

            0,

            "Issued"
        ))


        # =====================================================
        # UPDATE BOOK AVAILABILITY
        # =====================================================

        new_available = (
            book["available_quantity"] - 1
        )


        if new_available > 0:

            new_status = "Available"

        else:

            new_status = "All Issued"


        conn.execute("""
            UPDATE books

            SET

                available_quantity = ?,

                status = ?

            WHERE id = ?

        """, (

            new_available,

            new_status,

            book_id
        ))


        conn.commit()


        flash(
            "Book issued successfully!",
            "success"
        )


        return redirect(
            url_for("issue_return")
        )


    finally:

        conn.close()


# =========================================================
# RETURN BOOK
# =========================================================

@app.route(
    "/return_book",
    methods=["POST"]
)
def return_book():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    transaction_id = request.form.get(
        "transaction_id"
    )


    return_date = request.form.get(
        "return_date"
    )


    if not transaction_id:

        flash(
            "Please select an issued transaction.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    if not return_date:

        flash(
            "Please select return date.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    try:

        return_date_obj = datetime.strptime(
            return_date,
            "%Y-%m-%d"
        ).date()


    except ValueError:

        flash(
            "Invalid return date.",
            "danger"
        )

        return redirect(
            url_for("issue_return")
        )


    conn = get_db_connection()

    try:

        # =====================================================
        # GET TRANSACTION
        # =====================================================

        transaction = conn.execute("""
            SELECT *

            FROM transactions

            WHERE id = ?

        """, (
            transaction_id,
        )).fetchone()


        if not transaction:

            flash(
                "Transaction not found.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        if transaction["status"] == "Returned":

            flash(
                "This transaction is already returned.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        # =====================================================
        # GET DATES
        # =====================================================

        issue_date_obj = datetime.strptime(
            transaction["issue_date"],
            "%Y-%m-%d"
        ).date()


        due_date_obj = datetime.strptime(
            transaction["due_date"],
            "%Y-%m-%d"
        ).date()


        if return_date_obj < issue_date_obj:

            flash(
                "Return date cannot be before issue date.",
                "danger"
            )

            return redirect(
                url_for("issue_return")
            )


        # =====================================================
        # CALCULATE FINE
        # =====================================================

        late_days = (
            return_date_obj -
            due_date_obj
        ).days


        if late_days < 0:

            late_days = 0


        fine = (
            late_days *
            FINE_PER_DAY
        )


        # =====================================================
        # UPDATE TRANSACTION
        # =====================================================

        conn.execute("""
            UPDATE transactions

            SET

                return_date = ?,

                fine = ?,

                status = 'Returned'

            WHERE id = ?

        """, (

            return_date,

            fine,

            transaction_id
        ))


        # =====================================================
        # UPDATE BOOK
        # =====================================================

        book = conn.execute("""
            SELECT *

            FROM books

            WHERE id = ?

        """, (
            transaction["book_id"],
        )).fetchone()


        if book:

            new_available = (
                book["available_quantity"] + 1
            )


            if new_available > book["quantity"]:

                new_available = (
                    book["quantity"]
                )


            if new_available > 0:

                new_status = "Available"

            else:

                new_status = "All Issued"


            conn.execute("""
                UPDATE books

                SET

                    available_quantity = ?,

                    status = ?

                WHERE id = ?

            """, (

                new_available,

                new_status,

                transaction["book_id"]
            ))


        conn.commit()


        # =====================================================
        # SUCCESS MESSAGE
        # =====================================================

        if fine > 0:

            flash(
                f"Book returned successfully! "
                f"Late days: {late_days} | "
                f"Fine: ₹{fine}",
                "success"
            )

        else:

            flash(
                "Book returned successfully! Fine: ₹0",
                "success"
            )


        return redirect(
            url_for("issue_return")
        )


    finally:

        conn.close()


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )