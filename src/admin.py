import sqlite3
from getpass import getpass
from werkzeug.security import generate_password_hash
import sys

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} action")
    print("Actions: add, change, delete")
    sys.exit(1)

conn = sqlite3.connect("staff.db")
cur = conn.cursor()
cur.execute(f"""create table if not exists staff (
    id integer primary key autoincrement,
    username text,
    password text,
    type integer
)""")
conn.commit()

if sys.argv[1] == "add":
    username = input("Username: ").strip().lower()

    res = cur.execute("select username from staff where username=?", (username,)).fetchone()
    if res:
        print("Username already exists")
        sys.exit(1)

    password = getpass("Password: ")

    if getpass("Confirm: ") != password:
        print("Password does not match")
        sys.exit(1)
    if not username or not password:
        print("Username or password cannot be empty")
        sys.exit(1)

    cur.execute("insert into staff values (NULL, ?, ?, 1)", (username, generate_password_hash(password)))
    conn.commit()
elif sys.argv[1] == "change":
    username = input("Username: ").strip().lower()

    res = cur.execute("select username from staff where username=?", (username,)).fetchone()
    if not res:
        print("Username doesn't exist")
        sys.exit(1)

    password = getpass("Password: ")

    if getpass("Confirm: ") != password:
        print("Password does not match")
        sys.exit(1)
    if not username or not password:
        print("Username or password cannot be empty")
        sys.exit(1)

    cur.execute("update staff set password=? where username=?", (generate_password_hash(password), username))
    conn.commit()
elif sys.argv[1] == "delete":
    username = input("Username: ").strip().lower()

    res = cur.execute("select username from staff where username=?", (username,)).fetchone()
    if not res:
        print("Username doesn't exist")
        sys.exit(1)

    if input("Confirm username: ").strip().lower() != username:
        print("Usernames do not match")
        sys.exit(1)

    if not username:
        print("Username cannot be empty")
        sys.exit(1)

    cur.execute("delete from staff where username=?", (username,))
    conn.commit()
else:
    print(f"Usage: {sys.argv[0]} action")
    print("Actions: add, change, delete")
    sys.exit(1)