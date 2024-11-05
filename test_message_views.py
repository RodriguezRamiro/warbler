"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        db.create_all()

    def test_add_message(self):
        """Can use add a message?"""

        # change the session to mimic logging in,


        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # session setting is saved,
            # rest of test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_view_message(self):
        """Test if a user can view a message after adding it."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Create a message
            c.post("/messages/new", data={"text": "Hello"})

            # access the messages page to see if the message appears
            resp = c.get("/messages")

            self.assertIn(b"Hello", resp.data)  # Check if the message text is in the response

    def test_delete_message(self):
        """Test if a user can delete their message."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Create a message to delete
            c.post("/messages/new", data={"text": "This will be deleted"})

            msg = Message.query.one()
            msg_id = msg.id

            # delete the message
            resp = c.post(f"/messages/{msg_id}/delete")

            self.assertEqual(resp.status_code, 302)  # Should redirect after deletion
            self.assertIsNone(Message.query.get(msg_id))  # Ensure the message is gone

    def test_add_message_unauthenticated(self):
        """Test adding a message without being logged in."""
        resp = self.client.post("/messages/new", data={"text": "Hello"})

        # Expect a redirect to the login or an error page
        self.assertEqual(resp.status_code, 302)  # Redirect for unauthenticated access
