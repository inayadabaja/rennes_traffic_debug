import sqlite3

conn = sqlite3.connect("flask_monitoringdashboard.db")
cur = conn.cursor()

# Liste des tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [x[0] for x in cur.fetchall()]

print("TABLES :", tables)

# Nombre de lignes dans chaque table
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        count = cur.fetchone()[0]
        print(f"{t} : {count}")
    except Exception as e:
        print(f"{t} : ERREUR -> {e}")

conn.close()