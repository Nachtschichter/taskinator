#!/usr/bin/env python3
"""Password change script for Taskinator admin user"""
import sys
from passlib.context import CryptContext
import sqlite3

DB_PATH = "/home/storagebox/databases/taskinator/taskinator.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    
    # Hash new password
    new_hash = pwd_context.hash(new_password)
    
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
