import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), "test_sqlite.db")
print(f"Creating DB at {db_path}")

try:
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE stocks (date text, trans text, symbol text, qty real, price real)''')
    c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
    conn.commit()
    conn.close()
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
