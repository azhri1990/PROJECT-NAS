import sqlite3, os
from typing import List
class Memory:
    def __init__(self, db_path="memory.sqlite3"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)')
        conn.commit(); conn.close()
    def store(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO memories (key, value) VALUES (?, ?)", (key, value))
        conn.commit(); conn.close()
    def retrieve(self, query, limit=3):
        conn = sqlite3.connect(self.db_path)
        keywords = [w for w in query.lower().split() if len(w)>2]
        if not keywords:
            rows = conn.execute("SELECT key, value FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY timestamp DESC LIMIT ?", (f"%{query}%", f"%{query}%", limit)).fetchall()
        else:
            conditions = ["key LIKE ?" for _ in keywords] + ["value LIKE ?" for _ in keywords]
            params = [f"%{kw}%" for kw in keywords]*2
            rows = conn.execute("SELECT key, value FROM memories WHERE " + " OR ".join(conditions) + " ORDER BY timestamp DESC LIMIT ?", params + [limit]).fetchall()
        conn.close()
        return [f"{row[0]}: {row[1]}" for row in rows]
