import sqlite3
conn = sqlite3.connect('data/paodeamao.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([t[0] for t in tables])
conn.close()