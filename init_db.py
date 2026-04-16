import sqlite3

con = sqlite3.connect("database.db")
c = con.cursor()

con.execute("""
CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    category TEXT,
    file TEXT,
    quantity INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS borrow(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
book_id INTEGER,
borrow_date TEXT,
return_date TEXT,
status TEXT
)
""")

c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','admin','admin')")
c.execute("INSERT OR IGNORE INTO users VALUES (2,'user','user','user')")

con.commit()
con.close()