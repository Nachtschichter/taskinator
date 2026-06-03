#!/usr/bin/env python3
"""Password change script for Taskinator admin user"""
import sys
import os

# Ensure imports work when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.config import config
from backend.security import hash_password, verify_password
import sqlite3

DB_PATH = config.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")

def change_password(username, new_password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        print(f"❌ User '{username}' not found")
        conn.close()
        return False

    # Hash new password (Argon2id via shared security module)
    new_hash = hash_password(new_password)

    # Update password
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
    conn.commit()
    conn.close()

    print(f"✅ Password changed for user '{username}'")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: change_password.py <username> <new_password>")
        print("Example: change_password.py admin NewPass123!")
        sys.exit(1)

    change_password(sys.argv[1], sys.argv[2])
