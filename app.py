from flask import Flask, render_template, request, redirect, session, send_from_directory
import sqlite3, datetime, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret"

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# DATABASE CONNECTION
def db():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    return con


# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u, p)
        ).fetchone()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["id"] = user["id"]

            if user["role"] == "admin":
                return redirect("/")
            else:
                return redirect("/user_dashboard")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ADMIN DASHBOARD
@app.route("/")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    con = db()

    total = con.execute("SELECT COUNT(*) as c FROM books").fetchone()["c"]
    borrowed = con.execute("SELECT COUNT(*) as c FROM borrow WHERE status='borrowed'").fetchone()["c"]
    returned = con.execute("SELECT COUNT(*) as c FROM borrow WHERE status='returned'").fetchone()["c"]

    return render_template("dashboard.html",
                           total=total,
                           borrowed=borrowed,
                           returned=returned)


# USER DASHBOARD
@app.route("/user_dashboard")
def user_dashboard():
    if "user" not in session:
        return redirect("/login")

    con = db()

    data = con.execute("""
        SELECT books.title, borrow.borrow_date,
               borrow.return_date, borrow.status
        FROM borrow
        JOIN books ON books.id = borrow.book_id
        WHERE borrow.user_id=?
    """, (session["id"],)).fetchall()

    return render_template("user_dashboard.html", data=data)


# ADD BOOK
@app.route("/add_book", methods=["GET","POST"])
def add_book():
    if session.get("role") != "admin":
        return "Access Denied"

    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        quantity = request.form["quantity"]

        file = request.files["file"]
        filename = ""

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        con = db()
        con.execute("""
INSERT INTO books(title,author,category,file,quantity)
VALUES(?,?,?,?,?)
""", (title, author, category, filename, quantity))
        con.commit()

        return redirect("/books")

    return render_template("add_book.html")


# READ BOOK
@app.route("/read/<filename>")
def read_book(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# VIEW BOOKS
@app.route("/books")
def books():
    if "user" not in session:
        return redirect("/login")

    con = db()

    books = con.execute("SELECT * FROM books").fetchall()

    borrowed = con.execute("""
        SELECT book_id FROM borrow
        WHERE user_id=? AND status='borrowed'
    """, (session["id"],)).fetchall()

    borrowed_ids = [b["book_id"] for b in borrowed]

    return render_template("books.html",
                           books=books,
                           borrowed_ids=borrowed_ids)


# BORROW
@app.route("/borrow/<int:id>")
def borrow(id):
    if "user" not in session:
        return redirect("/login")

    con = db()

    today = datetime.date.today()
    return_date = today + datetime.timedelta(days=7)

    con.execute("""
        INSERT INTO borrow(user_id,book_id,borrow_date,return_date,status)
        VALUES(?,?,?,?,?)
    """, (session["id"], id, today, return_date, "borrowed"))

    con.commit()

    return redirect("/books")


# RETURN
@app.route("/return/<int:id>")
def return_book(id):
    if "user" not in session:
        return redirect("/login")

    con = db()
    today = datetime.date.today()

    con.execute("""
        UPDATE borrow
        SET status='returned',
            return_date=?   -- ✅ update actual return date
        WHERE book_id=? AND user_id=? AND status='borrowed'
    """, (today, id, session["id"]))

    con.commit()
    return redirect("/books")

# ISSUE BOOK (ADMIN)
@app.route("/issue", methods=["GET","POST"])
def issue():
    if session.get("role") != "admin":
        return "Access Denied"

    con = db()

    if request.method == "POST":
        user_id = request.form["user"]
        book_id = request.form["book"]

        today = datetime.date.today()
        return_date = today + datetime.timedelta(days=7)

        con.execute("""
            INSERT INTO borrow(user_id,book_id,borrow_date,return_date,status)
            VALUES(?,?,?,?,?)
        """, (user_id, book_id, today, return_date, "borrowed"))

        con.commit()

    users = con.execute("SELECT * FROM users WHERE role='user'").fetchall()
    books = con.execute("SELECT * FROM books").fetchall()

    return render_template("issue_book.html", users=users, books=books)


# USERS
@app.route("/users", methods=["GET","POST"])
def users():
    if session.get("role") != "admin":
        return "Access Denied"

    con = db()

    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        r = request.form["role"]

        con.execute("""
            INSERT INTO users(username,password,role)
            VALUES(?,?,?)
        """, (u, p, r))
        con.commit()

    data = con.execute("SELECT * FROM users").fetchall()

    return render_template("users.html", users=data)


# BORROW DETAILS (ADMIN)
@app.route("/borrow_details")
def borrow_details():
    if session.get("role") != "admin":
        return "Access Denied"

    con = db()

    data = con.execute("""
        SELECT users.username, books.title,
               borrow.borrow_date, borrow.return_date,
               borrow.status
        FROM borrow
        JOIN users ON users.id = borrow.user_id
        JOIN books ON books.id = borrow.book_id
        ORDER BY borrow.id DESC
    """).fetchall()

    return render_template("borrow_details.html", data=data)


# DELETE BOOK
@app.route("/delete_book/<int:id>")
def delete_book(id):
    if session.get("role") != "admin":
        return "Access Denied"

    con = db()
    con.execute("DELETE FROM books WHERE id=?", (id,))
    con.commit()

    return redirect("/books")


# DELETE USER  ✅ FIXED
@app.route("/delete_user/<int:id>")
def delete_user(id):
    if session.get("role") != "admin":
        return "Access Denied"

    con = db()
    con.execute("DELETE FROM users WHERE id=?", (id,))
    con.commit()

    return redirect("/users")


# Rimport os

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)