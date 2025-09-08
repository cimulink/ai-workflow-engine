import sqlite3

# Connect to the database
conn = sqlite3.connect('workflow.db')
cursor = conn.cursor()

# Query for pending documents
cursor.execute("SELECT document_id, status FROM documents WHERE status = 'pending_review'")
rows = cursor.fetchall()

print('Pending documents:')
for row in rows:
    print(f'  {row[0]}: {row[1]}')

conn.close()