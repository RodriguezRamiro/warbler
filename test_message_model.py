"""Message model tests."""

# Run these tests like:
#    python -m unittest test_message_model.py

import os
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows, Likes

# Set environmental variable for the test database
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import the app
from app import app

# Create tables (this is done once for all tests)
db.create_all()

class MessageModelTestCase(TestCase):
    """Test model for messages."""

    def setUp(self):
        """Set up test client and sample data."""
        db.drop_all()
        db.create_all()

        # Create a test user
        self.uid = 94566
        u = User.signup("testuser", "testuser@test.com", "password", None)
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)
        self.client = app.test_client()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()

    def test_message_model(self):
        """Test basic message model functionality."""
        # Create a message
        m = Message(
            text="a warble",
            user_id=self.uid
        )

        db.session.add(m)
        db.session.commit()

        # Check if the user has one message, and if the message's text is correct
        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, "a warble")

    def test_message_likes(self):
        """Test liking a message functionality."""
        # Create two messages
        m1 = Message(text="a warble", user_id=self.uid)
        m2 = Message(text="an interesting warble", user_id=self.uid)

        # Create another test user
        u = User.signup("anotheruser", "another@test.com", "password", None)
        uid = 888
        u.id = uid
        db.session.add_all([m1, m2, u])
        db.session.commit()

        # The second user likes the first message
        u.likes.append(m1)
        db.session.commit()

        # Check if the user has liked exactly one message and that it's the correct one
        likes = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(likes), 1)
        self.assertEqual(likes[0].message_id, m1.id)

    # Additional tests could be added here, e.g., for message deletion or user liking their own messages
    def test_message_creation_without_text(self):
        """Test that a message cannot be created without text."""
        with self.assertRaises(exc.IntegrityError):
            m = Message(user_id=self.uid)  # No text provided
            db.session.add(m)
            db.session.commit()

    def test_user_liking_own_message(self):
        """Test that a user cannot like their own message."""
        m = Message(text="another warble", user_id=self.uid)
        db.session.add(m)
        db.session.commit()

        # Attempt to like their own message
        self.u.likes.append(m)
        db.session.commit()

        # Assuming your application logic prevents this, check that the like was not added
        likes = Likes.query.filter(Likes.user_id == self.uid).all()
        self.assertEqual(len(likes), 0)

    def test_message_deletion(self):
        """Test that a message can be deleted."""
        m = Message(text="delete this message", user_id=self.uid)
        db.session.add(m)
        db.session.commit()

        # Delete the message
        db.session.delete(m)
        db.session.commit()

        # Ensure that the message no longer exists
        self.assertIsNone(Message.query.get(m.id))

