import os
import sys
import tempfile
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.user import create_user, login_user


class TestAuth(unittest.TestCase):

    def setUp(self):
        """Set up an in-memory-style test by using a temp database."""
        import sqlite3
        import app.models.user as user_module
        self.original_db_path = user_module.DB_PATH
        self.test_db_fd, self.test_db = tempfile.mkstemp(suffix=".db")
        os.close(self.test_db_fd)
        user_module.DB_PATH = self.test_db
        conn = sqlite3.connect(self.test_db)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        """Restore original DB path and remove test database."""
        import app.models.user as user_module
        user_module.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_create_user_success(self):
        result = create_user("test@example.com", "password123")
        self.assertTrue(result)

    def test_create_user_duplicate_email(self):
        create_user("dup@example.com", "password123")
        result = create_user("dup@example.com", "anotherpass")
        self.assertFalse(result)

    def test_login_user_success(self):
        create_user("login@example.com", "securepass")
        result = login_user("login@example.com", "securepass")
        self.assertTrue(result)

    def test_login_user_wrong_password(self):
        create_user("wrong@example.com", "correctpass")
        result = login_user("wrong@example.com", "wrongpass")
        self.assertFalse(result)

    def test_login_user_nonexistent(self):
        result = login_user("nobody@example.com", "anypass")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
