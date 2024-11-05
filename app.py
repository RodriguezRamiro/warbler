import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from forms import UserAddForm, LoginForm, MessageForm, ProfileEditForm, ChangePasswordForm
from models import db, connect_db, User, Follows, Message, Likes
CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

# Initialize app context for database connection and create tables
with app.app_context():
    db.create_all()

def check_auth(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            flash("Access unauthorized.", "danger")
            return redirect("/")
        val = f(*args, **kwargs)
        return val
    wrapper.__name__ = f.__name__
    return wrapper
##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    flash('sucess', 'You have logged out sucessfully.' )
    return redirect("/login")




##############################################################################
# General user routes:

@app.route('/users', methods=["GET", "POST"])
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if request.method == "POST":
        # Handle user creation logic here
        form = UserAddForm()  # Ensure form defined for adding users
        if form.validate_on_submit():
            try:
                user = User.signup(
                    username=form.username.data,
                    password=form.password.data,
                    email=form.email.data,
                    image_url=form.image_url.data or User.image_url.default.arg,
                )
                db.session.commit()
                flash("User created successfully!", "success")
                return redirect("/users")

            except IntegrityError:
                flash("Username already taken", "danger")
                return render_template('users/index.html', form=form)

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
@check_auth
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


# liked warbles route
@app.route('/users/<int:user_id>/liked_warbles')
@check_auth
def liked_warbles(user_id):
    """Show liked warbles for a specific user."""
    user = User.query.get_or_404(user_id)

    # fetch liked messages
    liked_warbles = Message.query.join(Likes).filter(Likes.user_id == user_id).all()

    return render_template('users/liked_warbles.html', user=user, liked_warbles=liked_warbles)


@app.route('/users/<int:user_id>/following')
@check_auth
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
@check_auth
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)



@app.route('/users/<int:user_id>/likes')
@check_auth
def users_likes(user_id):
    """Show list of followers of this user."""

    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
@check_auth
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
@check_auth
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
@check_auth
def edit_profile():
    """Update profile for current user."""

    user = g.user
    form = ProfileEditForm(obj=user)

    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            try:

                user.username = form.username.data
                user.email = form.email.data
                user.image_url = form.image_url.data
                user.header_image_url = form.header_image_url.data
                user.bio = form.bio.data
                user.location = form.location.data

                db.session.commit()

            except IntegrityError:
                flash("Username already taken", 'danger')
                return render_template('users/edit.html', form=form)

            return redirect(f"/users/{g.user.id}")

        else:
            flash("Incorrect Password", 'danger')
            return render_template('users/edit.html', form=form)

    else:
        return render_template('users/edit.html', form=form)

@app.route('/users/profile/password', methods=["GET", "POST"])
@check_auth
def change_password():
    """Change password for current user."""

    user = g.user
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if (form.new_password.data != form.new_password_match.data):
            flash("Non Matching Password", 'danger')
            return render_template('users/edit_password.html', form=form)

        elif User.authenticate(user.username, form.password.data):
            try:

                new_password = form.new_password.data

                user = User.edit_password(user.username, new_password)
                g.user.password = user.password

            except IntegrityError:
                flash("Username already taken", 'danger')
                return render_template('users/edit_password.html', form=form)

            return redirect(f"/users/{g.user.id}")

        else:
            flash("Incorrect Password", 'danger')
            return render_template('users/edit_password.html', form=form)

    else:
        return render_template('users/edit_password.html', form=form)



@app.route('/users/delete', methods=["POST"])
@check_auth
def delete_user():
    """Delete user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    try:
        user_to_delete = User.query.get(g.user.id)
        if not user_to_delete:
            flash("User not found.", "danger")
            return redirect("/")

        # Delete messages associated with the user
        Message.query.filter_by(user_id=user_to_delete.id).delete(synchronize_session='fetch')

        # Delete related follows entries
        Follows.query.filter(
            (Follows.user_following_id == user_to_delete.id) |
            (Follows.user_being_followed_id == user_to_delete.id)
        ).delete(synchronize_session='fetch')

        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        app.logger.error(f"Error deleting user: {str(e)}")
        flash("An error occurred while deleting the user.", "danger")

    return redirect("/signup")

@app.route('/users/add_like/<int:message_id>', methods=["POST"])
@check_auth
def like_message(message_id):
    """Like a message."""

    # Fetch the message or return a 404 if not found
    message = Message.query.get_or_404(message_id)

    # Check if the user is trying to like their own message
    if message.user_id == g.user.id:
        flash("You cannot like your own warble!", "error")
        return redirect(f"/messages/{message_id}")

    # Check if the user has already liked the message
    existing_like = Likes.query.filter_by(user_id=g.user.id, message_id=message_id).first()

    if not existing_like:
        # If the user has not liked it yet, create a new like
        like = Likes(user_id=g.user.id, message_id=message_id)
        db.session.add(like)
        flash("Warble liked!", "success")
    else:
        # If the user has already liked it, remove the like
        db.session.delete(existing_like)
        flash("Warble unliked!", "info")

    # Commit the session
    db.session.commit()

    return redirect(f"/messages/{message_id}")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
@check_auth
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    # Check if the user has liked the message
    user_liked = False
    if g.user:
        user_liked = any(like.user_id == g.user.id for like in msg.likes)

    return render_template('messages/show.html', message=msg, user_liked=user_liked)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        messages = (Message
                    .query
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        followings = [following.id for following in g.user.following]
        followings.append(g.user.id)
        likes = [like.id for like in g.user.likes]

        return render_template('home.html', messages=messages, followings=followings, likes=likes)

    else:
        return render_template('home-anon.html')

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req

@app.errorhandler(404)
def page_not_found(e):
    """NOT FOUND page 404 ERROR"""

    return render_template('users/404.html'), 404
