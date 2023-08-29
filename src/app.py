# app.py - main program
# Copyright (C) 2022  GSC Bravo

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime, timezone
from flask import Flask, render_template, redirect, request, session
from werkzeug.security import check_password_hash
import sqlite3
import os
import configparser
import string

parser = configparser.ConfigParser()

# create config if none created
if not os.path.isfile("config.toml"):
    with open("config.toml", "w") as f:
        parser['config'] = {
            "max_comments": 1000,
            "max_subject_length": 78,
            "max_name_length": 50,
            "max_comment_length": 2000,
            "default_name": "Guest",
            "site_name": "Infinity Forums",
            "site_description": "comments section",
            "default_board": "general"
        }
        parser.write(f)

# read config file
parser.read_file(open("config.toml"))

# max number of comments to store
MAX_COMMENTS = int(parser.get("config", "max_comments", fallback=1000))
# max chars in subject
MAX_SUBJECT_LENGTH = int(parser.get("config", "max_subject_length", fallback=78))
# max chars in name
MAX_NAME_LENGTH = int(parser.get("config", "max_name_length", fallback=50))
# max chars in comment
MAX_COMMENT_LENGTH = int(parser.get("config", "max_comment_length", fallback=2000))
# default name
DEFAULT_NAME = parser.get("config", "default_name", fallback="Guest")
# site name
SITE_NAME = parser.get("config", "site_name", fallback="Infinity Forums")
# site description
SITE_DESCRIPTION = parser.get("config", "site_description", fallback="comments section")
# default board name
DEFAULT_BOARD = parser.get("config", "default_board", fallback="general")

app = Flask(__name__)

# change this to something better in practice
app.config['SECRET_KEY'] = "CHANGE ME TO SOMETHING SECURE"

# jinja config
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

def staff_init():
    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()
    cur.execute(f"""create table if not exists staff (
        id integer primary key autoincrement,
        username text,
        password text
    )""")
staff_init()

# initialize database if doesn't exist
def db_init(board_name):
    conn = sqlite3.connect("board.db")
    cur = conn.cursor()
    cur.execute(f"""create table if not exists {board_name} (
        name text,
        subject text,
        replyto text,
        text text,
        date text
    )""")
    conn.commit()

# turn input to proper board name
def filter_name(str):
    allowed_chars = f"{string.digits}{string.ascii_letters}_"
    return "".join(c for c in str if c in allowed_chars).lstrip("1234567890")

@app.route("/")
def index():
    return redirect(f"/b/{DEFAULT_BOARD}/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user" in session:
            return redirect("/")
        return render_template("login.html")
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("error.html", error="Username or password cannot be empty")
    
    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    res = cur.execute("select * from staff where username=?", (username,)).fetchone()
    if not res:
        return render_template("error.html", error="Invalid login")

    if not check_password_hash(res[1], password):
        return render_template("error.html", error="Invalid login")

    session['user'] = username

    return redirect("/")

@app.route("/logout")
def logout():
    # remove user session
    session.pop("user", None)
    return redirect("/")

@app.route("/delete")
def delete():
    if "user" not in session:
        return redirect("/")
    
    board = filter_name(request.args.get("board", ""))
    post = request.args.get("post", "")

    if not post:
        if not board:
            return redirect("/")
        return redirect("/b/{board}/")
    
    if not post.isdigit():
        return render_template("error.html", error="Invalid ID")

    conn = sqlite3.connect("board.db")
    cur = conn.cursor()

    if not cur.execute(f'select name from sqlite_master where type="table" and name="{board}"').fetchall():
        return render_template("error.html", error="Board does not exist")

    cur.execute(f"delete from {board} where rowid=?", (post,))
    conn.commit()

    return redirect(f"/b/{board}/")

@app.route("/boards")
def list_boards():
    # get all boards and sort
    conn = sqlite3.connect("board.db")
    cur = conn.cursor()
    res = cur.execute('select name from sqlite_master where type="table"').fetchall()
    results = {}
    for item in res:
        # attach size
        item_size = cur.execute(f'select rowid from {item[0]} order by rowid desc limit 1').fetchone()
        results[item[0]] = item_size[0] if item_size is not None else 0

        # remove if no posts
        if results[item[0]] == 0:
            results.pop(item[0])
    results = {k: v for k, v in sorted(results.items(), key=lambda item: item[1], reverse=True)}
    return render_template("boards.html", results=results, site_name=SITE_NAME)

@app.route("/b/<board>/")
def load_board(board):
    # get posts
    req_board = filter_name(board.lower().strip())
    replyto = request.args.get("replyto", "")

    conn = sqlite3.connect("board.db")
    cur = conn.cursor()

    if not cur.execute(f'select name from sqlite_master where type="table" and name="{req_board}"').fetchall():
        return render_template("comments.html", replyto=replyto, board_name=req_board, comments=[], default_name=DEFAULT_NAME, site_name=SITE_NAME, site_description=SITE_DESCRIPTION)

    res = cur.execute(f'select rowid, * from {req_board}').fetchall()
    board_comments = []
    for index, comment in enumerate(res):
        board_comments.insert(0, {
            "id": comment[0],
            "name": comment[1],
            "subject": comment[2],
            "replyto": comment[3],
            "text": comment[4].split('\n'),
            "date": comment[5],
            "replies": []
        })

        # attach replies
        for j in range(index, -1, -1):
            if str(board_comments[j]['id']) == comment[3]:
                board_comments[j]['replies'].append(comment[0])

    return render_template("comments.html", replyto=replyto, board_name=req_board, comments=board_comments, default_name=DEFAULT_NAME, site_name=SITE_NAME, site_description=SITE_DESCRIPTION)

@app.route("/go", methods=["GET", "POST"])
def go_to_board():
    if request.method == "GET":
        return render_template("error.html", error="Method not allowed")

    # filter board name and make sure it doesn't start with a digit
    allowed_chars = f"{string.digits}{string.ascii_letters}_"
    redirect_board = "".join(c for c in request.form.get("board", "").lower().strip() if c in allowed_chars)
    if redirect_board[0].isdigit():
        return render_template("error.html", error="Board name must not start with a digit")
    redirect_board = redirect_board.lstrip("1234567890")

    if not redirect_board:
        return render_template("error.html", error="Board name must not be empty")
    return redirect(f"/b/{redirect_board}/")

@app.route("/b/<board>/submit", methods=["GET", "POST"])
def submit(board):
    if request.method == "GET":
        return redirect("/")
    # get form args name, subject, text
    # only text is going to be actually required to post
    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    text = request.form.get("text", "").strip()
    replyto = request.form.get("replyto", "").strip()

    req_board = filter_name(board.lower().strip())

    # if invalid reply to id
    if replyto and not replyto.isdigit():
        return render_template("error.html", error="Invalid reply ID")

    # if text is empty, error
    if not text:
        return render_template("error.html", error="Text box must not be empty")
    
    # limit subject length
    if len(subject) > MAX_SUBJECT_LENGTH:
        return render_template("error.html", error=f"Subject must be no more than {MAX_SUBJECT_LENGTH} characters")
    
    # limit name length
    if len(name) > MAX_NAME_LENGTH:
        return render_template("error.html", error=f"Name must be no more than {MAX_NAME_LENGTH} characters")

    # limit comment length
    if len(text) > MAX_COMMENT_LENGTH:
        return render_template("error.html", error=f"Comment must be no more than {MAX_COMMENT_LENGTH} characters")

    # if name is empty, set to default name
    if not name:
        name = DEFAULT_NAME

    # insert comment and return to post sent
    comment_data = (
        name,
        subject,
        replyto,
        text,
        str(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        )

    db_init(req_board)
    conn = sqlite3.connect("board.db")
    cur = conn.cursor()

    # drop oldest post if at limit
    if len(cur.execute(f'select * from {req_board}').fetchall()) >= MAX_COMMENTS:
        cur.execute(f'delete from {req_board} where rowid in (select rowid from {req_board} limit 1)')

    cur.execute(f'insert into {req_board} values (?, ?, ?, ?, ?)', comment_data)
    conn.commit()

    return redirect(f"/b/{req_board}/")

if __name__ == "__main__":
    app.run()
