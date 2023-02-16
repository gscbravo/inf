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
from tinydb import TinyDB, Query
from datetime import datetime

# max number of comments to store
MAX_COMMENTS = 1000
# max chars in comment
MAX_COMMENT_LENGTH = 2000
# default name
DEFAULT_NAME = 'Guest'
# site name
SITE_NAME = 'Infinity Forums'
# default board name
DEFAULT_BOARD = 'general'

app = Flask(__name__)

# comment list and number of total comments submitted
db = TinyDB('db.json')
q = Query()

if not db.search(q.total.exists()):
    db.insert({'total': 0})

@app.route('/')
def index():
    return redirect(f'/b/{DEFAULT_BOARD}/')

@app.route('/boards')
def list_boards():
    results = {}
    for line in db.search(q.board.exists()):
        results[line['board']] = len(line['posts'])
    results = {k: v for k, v in sorted(results.items(), key=lambda item: item[1], reverse=True)}
    return render_template('boards.html', results=results, site_name=SITE_NAME)

@app.route('/b/<board>/')
def load_board(board):
    req_board = board.lower().strip()
    # save space by just using empty array if no comments
    res = db.search(q.board == board)
    board_comments = res[0]['posts'] if len(res) else []
    tag = request.args.get('tag', '')
    return render_template('comments.html', comments=board_comments, tag=tag, default_name=DEFAULT_NAME, board=req_board, site_name=SITE_NAME)

@app.route('/go', methods=['GET', 'POST'])
def go_to_board():
    if request.method == 'GET':
        return render_template('error.html', error='Method not allowed')
    redirect_board = request.form.get('board', '').lower().strip()
    if not redirect_board:
        return render_template('error.html', error='Board name must not be empty')
    return redirect(f'/b/{redirect_board}/') if redirect_board else redirect('/')

@app.route('/b/<board>/submit', methods=['GET', 'POST'])
def submit(board):
    if request.method == 'GET':
        return redirect(f'/b/{board}/')
    # get form args name, subject, text, replyto; set to empty string if not represent
    # only text is going to be actually required to post
    name = request.form.get('name', '').strip()
    subject = request.form.get('subject', '').strip()
    text = request.form.get('text', '').strip()
    replyto = request.form.get('replyto', '').strip()

    req_board = board.lower().strip()

    # if replyto is set and not a number, error
    if replyto and not replyto.isdigit():
        return render_template('error.html', error='Comment ID is invalid')

    # if text is empty, error
    if not text:
        return render_template('error.html', error='Text box must not be empty')

    if len(text) > MAX_COMMENT_LENGTH:
        return render_template('error.html', error=f'Text must be no more than {MAX_COMMENT_LENGTH} characters')

    # if name is empty, set to default name
    if not name:
        name = DEFAULT_NAME

    # comment has been error checked, create board if not found
    res = db.search(q.board == board)
    if len(res) == 0:
        db.insert({'board': req_board, 'posts': []})
    data = db.search(q.board == board)[0]['posts']

    # remove oldest post if at maximum comment capacity
    if len(data) >= MAX_COMMENTS:
        data.pop()

    # increase post id
    old_total = db.search(q.total.exists())[0]['total']
    db.update({'total': old_total + 1}, q.total.exists())
    post_id = db.search(q.total.exists())[0]['total']

    # if comment is a replyto, add reply to comment it replies to
    if replyto:
        for comment in data:
            if comment['id'] == int(replyto):
                comment['replies'].append(post_id)

    # insert comment and return to post sent
    comment_data = {
        'name': name,
        'subject': subject,
        'text': text.split('\n'),
        'date': datetime.utcnow().isoformat(' ', 'seconds'),
        'id': post_id,
        'replyto': replyto,
        'replies': []
    }
    data.insert(0, comment_data)
    db.update({'posts': data}, q.board == req_board)
    return redirect(f'/b/{req_board}/')

if __name__ == '__main__':
    app.run()
