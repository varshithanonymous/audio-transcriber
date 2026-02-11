import sqlite3
import os

DB_NAME = "linguavoice.db"

def migrate():
    if not os.path.exists(DB_NAME):
        print("Database not found, nothing to migrate.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN target_language TEXT DEFAULT NULL")
        print("Successfully added target_language column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column target_language already exists.")
        else:
            print(f"Error migrating: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
