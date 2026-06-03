#!/usr/bin/env python3
"""
Taskinator Admin Password Change
Usage: python change_admin_password.py [new_password]
"""
import sqlite3
import sys
import os

# Ensure imports work when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.config import config
from backend.security import hash_password, verify_password

DB_PATH = config.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")

def change_password(new_password):
    new_hash = hash_password(new_password)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    user = cursor.fetchone()

    if not user:
        print("ERROR: Admin user not found!")
        conn.close()
        sys.exit(1)

    # Update password
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                   (new_hash, "admin"))
    conn.commit()

    # Verify
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("admin",))
    result = cursor.fetchone()
    verified = verify_password(new_password, result[0])

    conn.close()

    if verified:
        print(f"✅ Admin password updated successfully")
        print(f"   Hash: {result[0][:40]}...")
    else:
        print("❌ ERROR: Password verification failed!")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python change_admin_password.py <new_password>")
        print("Or:    docker compose exec taskinator python /app/change_admin_password.py <new_password>")
        sys.exit(1)

    new_password = sys.argv[1]
    change_password(new_password)
