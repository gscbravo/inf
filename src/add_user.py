import sqlite3
from getpass import getpass
from werkzeug.security import generate_password_hash
import sys

username = input("Username: ").strip()
password = getpass("Password: ")

if getpass("Confirm: ") != password:
    print("Password does not match")
    sys.exit(1)
if not username or not password:
    print("Username or password cannot be empty")
    sys.exit(1)

conn = sqlite3.connect("staff.db")
cur = conn.cursor()

cur.execute(f"""create table if not exists staff (
    id integer primary key autoincrement,
    username text,
    password text
)""")

conn.commit()

res = cur.execute("select username from staff where username=?", (username,)).fetchone()
if res:
    print("Username already exists")
    sys.exit(1)

cur.execute("insert into staff values (NULL, ?, ?)", (username, generate_password_hash(password)))
conn.commit()
