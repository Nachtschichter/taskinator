#!/usr/bin/env python3
"""
Taskinator Admin Passwort-Änderung
Usage: python change_admin_password.py [new_password]
"""
import sqlite3
import sys
from passlib.context import CryptContext

DB_PATH = "/app/data/taskinator.db"

def change_password(new_password):
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    new_hash = pwd_context.hash(new_password)
    
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
    verified = pwd_context.verify(new_password, result[0])
    
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
