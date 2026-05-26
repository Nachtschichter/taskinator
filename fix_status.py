#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/data/taskinator.db')
cursor = conn.cursor()

# Update status values to uppercase
cursor.execute("UPDATE tasks SET status = UPPER(status) WHERE status != UPPER(status)")
updated = cursor.rowcount
conn.commit()

print(f'Updated {updated} rows to uppercase')

# Verify
cursor.execute("SELECT DISTINCT status FROM tasks")
print('Status values:', cursor.fetchall())
conn.close()
