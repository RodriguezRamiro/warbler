# test_user_views.py
import os
from unittest import TestCase
from models import db, connect_db, Message, User, Likes, Follows


# Set an environmental variable to use a test database before importing the app
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app, CURR_USER_KEY

# Create tables once for all tests, delete and re-create fresh data for each test
db.create_all()

# Disable CSRF protection in WTForms for easier testing
app.config['WTF_CSRF_ENABLED'] = False

class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client and sample data."""
        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        # Set up a sample user
        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 8989
        self.testuser.id = self.testuser_id

        # Additional users for testing
        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u1_id = 778
        self.u1.id = self.u1_id

        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u2_id = 884
        self.u2.id = self.u2_id

        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

    def tearDown(self):
        """Clean up any fouled transactions."""
        try:
            db.session.rollback()
        except Exception as e:
            print(f"Error during rollback: {e}")
        finally:
            db.drop_all()
            db.create_all()

    def test_users_index(self):
        """Test that the user index displays all users."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/users")
            self.assertEqual(resp.status_code, 200, "Response should be OK")

            html = str(resp.data)
            self.assertIn("@testuser", html, "User @testuser should be in response")
            self.assertIn("@abc", html, "User @abc should be in response")
            self.assertIn("@efg", html, "User @efg should be in response")
            self.assertIn("@hij", html, "User @hij should be in response")
            self.assertIn("@testing", html, "User @testing should be in response")

    def test_users_search(self):
        """Test that the user search works correctly."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/users?q=test")
            self.assertEqual(resp.status_code, 200, "Response should be OK")

            html = str(resp.data)
            self.assertIn("@testuser", html, "User @testuser should appear in search results")
            self.assertIn("@testing", html, "User @testing should appear in search results")

            self.assertNotIn("@abc", html, "User @abc should NOT appear in search results")
            self.assertNotIn("@efg", html, "User @efg should NOT appear in search results")
            self.assertNotIn("@hij", html, "User @hij should NOT appear in search results")

    def test_user_show(self):
        """Test that user profile page shows correct user."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(f"/users/{self.testuser_id}")
            self.assertEqual(resp.status_code, 200, "Response should be OK")

            html = str(resp.data)
            self.assertIn("@testuser", html, "User @testuser should be in profile page response")

    def test_unauthorized_show(self):
        """Test that unauthorized access to a user profile redirects."""
        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 302, "Response should be a redirect")
            self.assertNotIn("@testuser", str(resp.data), "User @testuser should not be in response without login")
