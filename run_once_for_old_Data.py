import sqlite3

DB_FILE = "transcriptions.db"
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# Add language column if missing
try:
    cur.execute("ALTER TABLE transcripts ADD COLUMN language TEXT")
    conn.commit()
    print("✅ Added 'language' column")
except sqlite3.OperationalError:
    print("ℹ️ 'language' column already exists")

conn.close()


conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute("UPDATE transcripts SET language = 'unknown' WHERE language IS NULL")
conn.commit()
conn.close()
