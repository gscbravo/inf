# inf

## About

An infinitely large [textboard](https://en.wikipedia.org/wiki/Textboard) model
showcasing a concept for an Internet forum that has the possibility of an
infinite amount of topics at the discretion of visitors. Boards are created
upon their URL being visited, with boards being listed upon a comment being
posted on the board. To conserve storage space, there is a limit on the number
of comments a board can have, with old comments being removed to make room for
new comments.

Currently, no registration is required to comment on the forum. Posts are
stored in SQLite. Each comment is assigned a comment number to uniquely
identify it. A board can be created using the search at the top of the main
page, or by typing a URL in the form of `/b/<board>`. Board names
are case insensitive.

The defaults for the forum can be configured in the file `config.toml` that is
created once the program is run. Config file is read upon the program starting,
so it will have to be restarted if config file changes are made.

You can greentext by starting a line with the ">" character. You can orangetext
by starting a line with the "<" character. Boards can use the letters of the
alphabet, as well as numbers, however, they cannot start with a number due to
technical limitations on behalf of SQLite.

### Defaults
- Maximum number of comments per board: `1000`
- Maximum subject length: `78`
- Maximum name length: `50`
- Maximum comment length: `2000`
- Default post name: `Guest`
- Site name: `Infinity Forums`
- Site description: `comments section`
- Default board: `general`

### Config

Lines not present will be replaced with the default value. Only the `[config]`
line is required. Place the config in `src/config.toml`.

```
[config]
max_comments = 1000
max_subject_length = 78
max_name_length = 50
max_comment_length = 2000
default_name = Guest
site_name = Infinity Forums
site_description = comments section
default_board = general
```

## Usage

For simple development.

```
pip3 install flask
cd src
flask run
```

Then you can create an admin account using `add_user.py`, which will store the account information
in `staff.db`. You can use this to delete comments.

```
python3 add_user.py
```

When in production, use a WSGI server such as [Gunicorn](https://gunicorn.org/)
with [Nginx](https://nginx.org/).

## TODO

- [ ] Website admin area to configure settings
- [ ] Prompt for admin account creation upon first startup of website
- [ ] Tripcodes
- [ ] Image upload
- [ ] Post as staff
- [ ] Store date and time as Unix timestamp
- [ ] Log IPs for better moderation
- [ ] Reply to multiple comments
- [ ] Code blocks
