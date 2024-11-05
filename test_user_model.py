"""User model tests."""

# Run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows

# Set environmental variable for the test database
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# import the app
from app import app

# Create all tables (only once for all tests)
db.create_all()

class UserModelTestCase(TestCase):
    """Test model for users."""

    def setUp(self):
        """Create test client and sample data."""
        db.drop_all()
        db.create_all()

        # Create two test users
        u1 = User.signup("testuser1", "email1@test.com", "password", None)
        u1.id = 1111

        u2 = User.signup("testuser2", "email2@test.com", "password", None)
        u2.id = 2222

        db.session.commit()

        self.u1 = User.query.get(1111)
        self.u2 = User.query.get(2222)

        self.client = app.test_client()

    def tearDown(self):
        """Clean up fouled transactions after each test."""
        try:
            db.session.rollback()
        except Exception as e:
            print(f"Error during rollback: {e}")
        finally:
            db.drop_all()
            db.create_all()

    def test_user_model(self):
        """Test basic user model functionality."""
        u = User(
            email="testuser3@test.com",
            username="testuser3",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers initially
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_follows(self):
        """Test follow functionality."""
        self.u1.following.append(self.u2)
        db.session.commit()

        # Test if u1 follows u2 and u2 has 1 follower
        self.assertEqual(len(self.u1.following), 1)
        self.assertEqual(len(self.u2.followers), 1)

        # Test if u1 is following u2 and u2 is followed by u1
        self.assertEqual(self.u1.following[0].id, self.u2.id)
        self.assertEqual(self.u2.followers[0].id, self.u1.id)

        # Test if u2 is not following anyone and u1 has no followers
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u1.followers), 0)

    def test_is_following(self):
        """Test is_following method."""
        self.u1.following.append(self.u2)
        db.session.commit()

        # u1 should be following u2
        self.assertTrue(self.u1.is_following(self.u2))
        # u2 should not be following u1
        self.assertFalse(self.u2.is_following(self.u1))

    ####
    # Signup Tests
    ####

    def test_valid_signup(self):
        """Test valid signup."""
        u3 = User.signup("testuser3", "email3@test.com", "password", None)
        u3.id = 3333
        db.session.commit()

        u_test = User.query.get(3333)
        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.username, "testuser3")
        self.assertEqual(u_test.email, "email3@test.com")
        # Bcrypt strings should start with $2b$
        self.assertTrue(u_test.password.startswith("$2b$"))

    def test_invalid_username_signup(self):
        """Test signup with invalid username (IntegrityError)."""
        u4 = User.signup(None, "email4@test.com", "password", None)
        with self.assertRaises(exc.IntegrityError):
            db.session.commit()

    def test_invalid_password_signup(self):
        """Test signup with invalid password."""
        # Test with empty password
        with self.assertRaises(ValueError):
            User.signup("testuser", "email@test.com", "", None)

        # Test with None password
        with self.assertRaises(ValueError):
            User.signup("testuser", "email@test.com", None, None)

    ####
    # Authentication Tests
    ####

    def test_valid_authentication(self):
        """Test valid authentication."""
        u = User.authenticate(self.u1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.u1.id)

    def test_invalid_username(self):
        """Test invalid username authentication."""
        self.assertFalse(User.authenticate("invalidusername", "password"))

    def test_wrong_password(self):
        """Test wrong password authentication."""
        self.assertFalse(User.authenticate(self.u1.username, "wrongpassword"))
