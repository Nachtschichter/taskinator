#!/usr/bin/env python3
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else '/app/data/taskinator.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Map German to English priority values
priority_map = {
    'niedrig': 'LOW',
    'mittel': 'MEDIUM',
    'hoch': 'HIGH'
}

# Update priority values
cursor.execute("SELECT DISTINCT priority FROM tasks")
existing = cursor.fetchall()
print(f'Existing priorities: {[p[0] for p in existing]}')

for german, english in priority_map.items():
    cursor.execute("UPDATE tasks SET priority = ? WHERE priority = ?", (english, german))
    if cursor.rowcount > 0:
        print(f'Migrated {cursor.rowcount} tasks from {german} to {english}')

conn.commit()

# Verify
cursor.execute("SELECT DISTINCT priority FROM tasks")
result = cursor.fetchall()
print(f'Updated priorities: {[p[0] for p in result]}')

conn.close()
print('Priority migration complete!')
