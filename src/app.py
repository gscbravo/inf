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

from flask import Flask, render_template, redirect, request
from datetime import datetime

# max number of comments to store
MAX_COMMENTS = 1000
# max chars in comment
MAX_COMMENT_LENGTH = 2000
# default name
DEFAULT_NAME = "Guest"
# site name
SITE_NAME = "Infinity Forums"
# default board name
DEFAULT_BOARD = "index"

app = Flask(__name__)

# comment list and number of total posts submitted
comments = {}
posts = 0

@app.route("/")
def index():
    return redirect(f"/b/{DEFAULT_BOARD}/")

@app.route("/boards")
def list_boards():
    return render_template("boards.html", all_boards=list(comments.keys()), site_name=SITE_NAME)

@app.route("/b/<board>/")
def load_board(board):
    # save space by just using empty array if no comments
    board_comments = comments[board] if board in comments else []
    tag = request.args.get("tag", "")
    return render_template("comments.html", comments=board_comments, tag=tag, default_name=DEFAULT_NAME, board=board, site_name=SITE_NAME)

@app.route("/go", methods=["GET", "POST"])
def go_to_board():
    if request.method == "GET":
        return render_template("error.html", error="Method not allowed")
    redirect_board = request.form.get("board", "").strip()
    if not redirect_board:
        return render_template("error.html", error="Board name must not be empty")
    return redirect(f"/b/{redirect_board}/") if redirect_board else redirect("/")

@app.route("/b/<board>/submit", methods=["GET", "POST"])
def submit(board):
    if request.method == "GET":
        return render_template("error.html", error="Method not allowed")
    # get form args name, subject, text, replyto; set to empty string if not represent
    # only text is going to be actually required to post
    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    text = request.form.get("text", "").strip()
    replyto = request.form.get("replyto", "").strip()

    # if replyto is set and not a number, error
    if replyto and not replyto.isdigit():
        return render_template("error.html", error="Comment ID is invalid")

    # if text is empty, error
    if not text:
        return render_template("error.html", error="Text box must not be empty")

    if len(text) > MAX_COMMENT_LENGTH:
        return render_template("error.html", error=f"Text must be no more than {MAX_COMMENT_LENGTH} characters")

    # if name is empty, set to default name
    if not name:
        name = DEFAULT_NAME

    # comment has been error checked, create board if not found
    if board not in comments:
        comments[board] = []
    current_board = comments[board]

    # remove oldest post if at maximum comment capacity
    if len(current_board) >= MAX_COMMENTS:
        current_board.pop()

    # increase post id
    global posts
    posts += 1

    # if comment is a replyto, add reply to comment it replies to
    if replyto:
        for comment in current_board:
            if comment['id'] == int(replyto):
                comment['replies'].append(posts)

    # insert comment and return to post sent
    comment_data = {
        "name": name,
        "subject": subject,
        "text": text.split("\n"),
        "date": datetime.utcnow().isoformat(" ", "seconds"),
        "id": posts,
        "replyto": replyto,
        "replies": []
    }
    current_board.insert(0, comment_data)
    return redirect(f"/b/{board}/")

if __name__ == "__main__":
    app.run()
