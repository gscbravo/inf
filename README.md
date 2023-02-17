# inf

## About

An infinitely large [textboard](https://en.wikipedia.org/wiki/Textboard) model
showcasing a concept for an Internet forum that has the possibility of an
infinite amount of topics at the discretion of visitors. Boards are created
upon their URL being visited, with boards being listed upon a comment being
posted on the board. To conserve storage space, there is a limit on the number
of comments a board can have, with old comments being removed to make room for
new comments.

Currently, no registration is required to comment on the forum or create
a board. Posts are stored in JSON. A board can be created using the search
at the top of the main page, or by typing a URL in the form of `/b/<board>`.
Each comment is assigned a comment number to uniquely identify it. Board names
are case insensitive.

The defaults for the forum are found in variables at the top of `app.py`.

### Defaults
- Maximum number of comments per board: `1000`
- Maximum comment length: `2000`
- Default comment name: `Guest`
- Default site name: `Infinity Forums`
- Default board: `general`

## Usage

```
pip3 install -r requirements.txt
cd src
flask run
```

When in production, use a WSGI server such as [Gunicorn](https://gunicorn.org/)
with [Nginx](https://nginx.org/).

## TODO

- [ ] Replace JSON with SQLite for better locking, can't be bother to right now
	- [ ] Or lazily use a bunch of locks everywhere and keep TinyDB
		- find a lock that works across multiple processes, not threading.Lock
- [ ] Tripcodes
- [ ] Image upload
- [ ] Moderation of comments
- [ ] Reply to multiple posts
