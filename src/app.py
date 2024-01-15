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
from uuid import uuid4
from flask import Flask, render_template, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import configparser
import string

app = Flask(__name__)

# CHANGE THIS!!!
app.config['SECRET_KEY'] = "CHANGE ME TO SOMETHING SECURE"

parser = configparser.ConfigParser()

# create config if none created
if not os.path.isfile("config.toml"):
    with open("config.toml", "w") as f:
        parser['config'] = {
            "max_comments": 1000,
            "max_subject_length": 78,
            "max_report_length": 78,
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
# max chars in report reason
MAX_REPORT_LENGTH = int(parser.get("config", "max_report_length", fallback=78))
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

# jinja config
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

def staff_init():
    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()
    cur.execute('''create table if not exists staff (
        id integer primary key autoincrement,
        username text,
        password text,
        type integer
    )''')
    cur.execute('''create table if not exists reports (
        board text,
        postid integer,
        reason text
    )''')
    cur.execute('''create table if not exists meta (
        field text,
        message text
    )''')
    cur.execute('''create table if not exists tokens (
        token text
    )''')
staff_init()

# turn input to proper board name
def filter_name(str):
    allowed_chars = f"{string.digits}{string.ascii_letters}"
    return "".join(c for c in str if c in allowed_chars).lstrip("1234567890")

# filter usernames
def filter_username(str):
    allowed_chars = f"{string.digits}{string.ascii_letters}_"
    return "".join(c for c in str if c in allowed_chars)

# check if user has type 0 aka admin status
def is_admin(username):
    with sqlite3.connect("staff.db") as conn:
        cur = conn.cursor()
        authlevel = cur.execute('select type from staff where username=?', (username,)).fetchone()[0]
    return authlevel == 0

@app.before_request
def before_request():
    if "user" in session:
        with sqlite3.connect("staff.db") as conn:
            cur = conn.cursor()
            # if session user is not in db then logout
            if not cur.execute('select username from staff where username=?', (session['user'],)).fetchone():
                session.pop("user", None)
                return redirect("/")

@app.route("/")
def index():
    return redirect(f"/b/{DEFAULT_BOARD}/")

@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    # get accouncement
    announceres = cur.execute('select * from meta where field="announce"').fetchone()
    if announceres:
        announce = announceres[1]
    else:
        announce = ""

    stafflist = ()
    tokenlist = ()

    # get list of staff and tokens
    adminstatus = False
    if is_admin(session['user']):
        stafflist = cur.execute('select username, type from staff').fetchall()
        tokenlist = cur.execute('select token from tokens').fetchall()
        adminstatus = True

    return render_template("admin.html", announce=announce, staff=stafflist, tokens=tokenlist, admin=adminstatus)

@app.route("/gentoken", methods=["GET", "POST"])
def gentoken():
    if "user" not in session or request.method == "GET" or not is_admin(session['user']):
        return redirect("/")

    # uuid4 token
    token = uuid4().hex

    with sqlite3.connect("staff.db") as conn:
        cur = conn.cursor()

        # if code somehow manages to generate an identical token, generate until it doesnt
        while len(cur.execute('select * from tokens where token=?', (token,)).fetchall()) > 0:
            token = uuid4().hex

        cur.execute('insert into tokens values(?)', (token,))
        conn.commit()

    return redirect("/admin")

@app.route("/deltoken", methods=["GET", "POST"])
def deltoken():
    if "user" not in session or request.method == "GET" or not is_admin(session['user']):
        return redirect("/")

    token = request.form.get("token", "")

    # delete requested token
    with sqlite3.connect("staff.db") as conn:
        cur = conn.cursor()
        cur.execute('delete from tokens where token=?', (token,))
        conn.commit()

    return redirect("/admin")

@app.route("/delacct", methods=["GET", "POST"])
def delacct():
    if "user" not in session or request.method == "GET" or not is_admin(session['user']):
        return redirect("/")

    username = request.form.get("username", "")

    if not username:
        return render_template("error.html", error="Username cannot be empty")

    with sqlite3.connect("staff.db") as conn:
        cur = conn.cursor()

        res = cur.execute("select username from staff where username=?", (username,)).fetchone()
        if not res:
            return render_template("error.html", error="Username doesn't exist")

        # delete user
        cur.execute("delete from staff where username=?", (username,))
        conn.commit()

        if session['user'] == res[0]:
            return redirect("/logout")

    return redirect("/admin")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        token = request.args.get("token", "")
        with sqlite3.connect("staff.db") as conn:
            cur = conn.cursor()

            # if token is not valid then dont show register page
            if len(cur.execute('select * from tokens where token=?', (token,)).fetchall()) == 0:
                return redirect("/")

            return render_template("register.html", token=token)

    type = request.form.get("type", "")

    # if type isnt either 0 admin or 1 mod escape
    if type != "1" and type != "0":
        return redirect("/")

    if type == "1":
        # if trying to register a mod then check to make sure token is valid
        token = request.form.get("token", "")
        with sqlite3.connect("staff.db") as conn:
            cur = conn.cursor()
            if len(cur.execute('select * from tokens where token=?', (token,)).fetchall()) == 0:
                return redirect("/")
    elif type == "0":
        # if trying to register an admin there must not already be one
        with sqlite3.connect("staff.db") as conn:
            cur = conn.cursor()
            if len(cur.execute('select * from staff where type=0').fetchall()) != 0:
                return redirect("/")

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not username or not password or not confirm:
        return render_template("error.html", error="Fields cannot be empty")

    if password != confirm:
        return render_template("error.html", error="Passwords do not match")

    # make sure usernames use only letters and numbers
    if not set(username) <= frozenset(f"{string.digits}{string.ascii_letters}_"):
        return render_template("error.html", error="Username can only use letters, digits, and underscores")
    username = filter_username(username)

    with sqlite3.connect("staff.db") as conn:
        cur = conn.cursor()
        if cur.execute('select username from staff where username=?', (username,)).fetchone():
            return render_template("error.html", error="Username taken")

        if type == "1":
            # create user and delete token
            cur.execute('insert into staff values (NULL, ?, ?, 1)', (username, generate_password_hash(password)))
            cur.execute('delete from tokens where token=?', (token,))
            # redirect if admin is creating user
            if "user" in session:
                return redirect("/admin")
        elif type == "0":
            cur.execute('insert into staff values (NULL, ?, ?, 0)', (username, generate_password_hash(password)))
        conn.commit()

    return render_template("error.html", error=f"Successfully registered {username}", type="register")

@app.route("/announce", methods=["GET", "POST"])
def announce():
    if "user" not in session or request.method == "GET":
        return redirect("/")

    announce = request.form.get("announce", "").strip()

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    if cur.execute('select * from meta where field="announce"').fetchone():
        cur.execute('update meta set message=? where field="announce"', (announce,))
    else:
        cur.execute('insert into meta values ("announce", ?)', (announce,))
    conn.commit()

    return redirect("/admin")

@app.route("/reports")
def list_reports():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    conn2 = sqlite3.connect("board.db")
    cur2 = conn2.cursor()

    res = cur.execute('select distinct board from reports').fetchall()
    reported_boards = []
    for board in res:
        res2 = cur.execute('select * from reports where board=?', (board[0],)).fetchall()
        available = []
        for r in res2:
            potential = cur2.execute(f'select * from {board[0]} where id=?', (r[1],)).fetchone()
            if potential:
                available.append(potential)

        reported_boards.append({
            "board": board[0],
            "size": len(available)
        })

    return render_template("reportlist.html", reports=reported_boards)

@app.route("/reports/<board>/")
def reports(board):
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    conn2 = sqlite3.connect("board.db")
    cur2 = conn2.cursor()

    reports = cur.execute('select * from reports where board=?', (board,)).fetchall()
    reported_comments = []
    for report in reports:
        comment = cur2.execute(f'select * from {report[0]} where id=?', (report[1],)).fetchone()
        if comment:
            reported_comments.append({
                "board": report[0],
                "id": comment[0],
                "name": comment[1],
                "subject": comment[2],
                "replyto": comment[3],
                "text": comment[4].split('\n'),
                "date": comment[5],
                "staff": comment[6],
                "reason": report[2]
            })

    return render_template("reports.html", reports=reported_comments, board=board)

@app.route("/changepassword", methods=["GET", "POST"])
def changepassword():
    if "user" not in session or request.method == "GET":
        return redirect("/")

    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    # empty fields
    if not password or not confirm:
        return render_template("error.html", error="Password cannot be empty")

    # typed incorrectly
    if password != confirm:
        return render_template("error.html", error="Passwords must match")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    # username not found
    if not cur.execute('select username from staff where username=?', (session['user'],)).fetchone():
        return render_template("error.html", error="Username does not exist")

    cur.execute('update staff set password=? where username=?', (generate_password_hash(password), session['user']))
    conn.commit()

    return render_template("error.html", error="Password successfully changed", type="noerror")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user" in session:
            return redirect("/")

        with sqlite3.connect("staff.db") as conn:
            cur = conn.cursor()
            if len(cur.execute('select * from staff where type=0').fetchall()) == 0:
                return render_template("setup.html")

        return render_template("login.html")

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("error.html", error="Username or password cannot be empty")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    # check if username not found
    res = cur.execute('select * from staff where username=?', (username,)).fetchone()
    if not res:
        return render_template("error.html", error="Invalid login")

    # check if password correct
    if not check_password_hash(res[2], password):
        return render_template("error.html", error="Invalid login")

    session['user'] = res[1]

    return redirect("/")

@app.route("/logout")
def logout():
    # remove user session
    session.pop("user", None)
    return redirect("/")

@app.route("/delete", methods=["GET", "POST"])
def delete():
    if "user" not in session or request.method == "GET":
        return redirect("/")

    board = filter_name(request.form.get("board", ""))
    post = request.form.get("post", "")

    admin = request.args.get("admin", "")

    # empty fields
    if not post:
        if not board:
            return redirect("/")
        return redirect("/b/{board}/")

    # post not a number
    if not post.isdigit():
        return render_template("error.html", error="Invalid ID")

    # don't delete from sqlite meta table
    if board == "sqlite_sequence":
        return render_template("error.html", error="Board does not exist")

    conn = sqlite3.connect("board.db")
    cur = conn.cursor()

    # board doesnt exist
    if not cur.execute(f'select name from sqlite_master where type="table" and name="{board}"').fetchall():
        return render_template("error.html", error="Board does not exist")

    cur.execute(f'delete from {board} where id=?', (post,))
    conn.commit()

    if admin:
        return redirect(f"/reports/{board}/")

    return redirect(f"/b/{board}/")

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "GET":
        board = request.args.get("board", "")
        post = request.args.get("post", "")
        return render_template("reportpost.html", board=board, post=post)

    board = filter_name(request.form.get("board", ""))
    post = request.form.get("post", "")
    reason = request.form.get("reason", "").strip()

    if not reason:
        return render_template("error.html", error="Specify a reason")

    if len(reason) > MAX_REPORT_LENGTH:
        return render_template("error.html", error=f"Reason must be under {MAX_REPORT_LENGTH} characters")

    if not post:
        if not board:
            return redirect("/")
        return redirect("/b/{board}/")

    if not post.isdigit():
        return render_template("error.html", error="Invalid ID")

    if board == "sqlite_sequence":
        return render_template("error.html", error="Board does not exist")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    conn2 = sqlite3.connect("board.db")
    cur2 = conn2.cursor()

    if not cur2.execute(f'select name from sqlite_master where type="table" and name="{board}"').fetchall():
        return render_template("error.html", error="Board does not exist")

    # check if post exists
    if not cur2.execute(f'select id from {board} where id=?', (post,)).fetchall():
        return render_template("error.html", error="Post does not exist")

    # check if report already sent
    if cur.execute('select * from reports where board=? and postid=?', (board, post)).fetchall():
        return redirect(f"/b/{board}/")

    cur.execute('insert into reports values (?, ?, ?)', (board, post, reason))
    conn.commit()

    return redirect(f"/b/{board}/")

@app.route("/unreport", methods=["GET", "POST"])
def unreport():
    if "user" not in session or request.method == "GET":
        return redirect("/")

    board = filter_name(request.form.get("board", ""))
    post = request.form.get("post", "")

    if not board or not post:
        return render_template("error.html", error="Board or post must not be empty")

    conn = sqlite3.connect("staff.db")
    cur = conn.cursor()

    if not cur.execute('select * from reports where board=? and postid=?', (board, post)).fetchall():
        return render_template("error.html", error="Post not reported")

    cur.execute('delete from reports where board=? and postid=?', (board, post))
    conn.commit()

    return redirect(f"/reports/{board}/")

@app.route("/boards")
def list_boards():
    # get all boards and sort
    conn = sqlite3.connect("board.db")
    cur = conn.cursor()
    res = cur.execute('select name from sqlite_master where type="table" and name!="sqlite_sequence"').fetchall()
    results = {}
    for item in res:
        # attach size
        item_size = cur.execute(f'select max(id) from {item[0]}').fetchone()
        results[item[0]] = item_size[0] if item_size is not None else 0

        # remove if no posts
        if results[item[0]] == 0 or results[item[0]] == None:
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

    staffconn = sqlite3.connect("staff.db")
    staffcur = staffconn.cursor()

    announceres = staffcur.execute('select * from meta where field="announce"').fetchone()
    if announceres:
        announce = announceres[1]
    else:
        announce = ""

    if not cur.execute(f'select name from sqlite_master where type="table" and name="{req_board}"').fetchall():
        return render_template("comments.html", replyto=replyto, board_name=req_board, comments=[], default_name=DEFAULT_NAME, site_name=SITE_NAME, site_description=SITE_DESCRIPTION, announce=announce.split("\n"))

    res = cur.execute(f'select * from {req_board}').fetchall()
    board_comments = []
    for index, comment in enumerate(res):
        commentauth = -1
        if comment[6]:
            commentauthres = staffcur.execute('select type from staff where username=?', (comment[6],)).fetchone()
            if commentauthres is not None:
                commentauth = commentauthres[0]

        board_comments.insert(0, {
            "id": comment[0],
            "name": comment[1],
            "subject": comment[2],
            "replyto": comment[3],
            "text": comment[4].split('\n'),
            "date": comment[5],
            "replies": [item[0] for item in cur.execute(f'select id from {req_board} where replyto=? and id>=?', (comment[0], comment[0]))],
            "staff": comment[6],
            "type": commentauth
        })

    return render_template("comments.html", replyto=replyto, board_name=req_board, comments=board_comments, default_name=DEFAULT_NAME, site_name=SITE_NAME, site_description=SITE_DESCRIPTION, announce=announce.split("\n"))

@app.route("/go", methods=["GET", "POST"])
def go_to_board():
    if request.method == "GET":
        return redirect("/")

    # filter board name and make sure it doesn't start with a digit
    allowed_chars = f"{string.digits}{string.ascii_letters}"
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
        return redirect(f"/b/{board}/")
    # get form args name, subject, text
    # only text is going to be actually required to post
    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    text = request.form.get("text", "").strip()
    replyto = request.form.get("replyto", "").strip()
    staff = request.form.get("staff", "").strip()

    if "user" in session and staff:
        staff = session['user']
    else:
        staff = ""

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
        str(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        staff
    )

    conn = sqlite3.connect("board.db")
    cur = conn.cursor()

    # initialize db
    cur.execute(f'''create table if not exists {req_board} (
        id integer primary key autoincrement,
        name text,
        subject text,
        replyto text,
        text text,
        date text,
        staff text
    )''')
    conn.commit()

    # drop oldest post if at limit
    if len(cur.execute(f'select * from {req_board}').fetchall()) >= MAX_COMMENTS:
        cur.execute(f'delete from {req_board} where rowid in (select rowid from {req_board} limit 1)')

    cur.execute(f'insert into {req_board} values (NULL, ?, ?, ?, ?, ?, ?)', comment_data)
    conn.commit()

    return redirect(f"/b/{req_board}/")

if __name__ == "__main__":
    app.run()
