import sqlite3

db = sqlite3.connect('updating.db')

c = db.cursor()
#   table submission:
#   size, tier, names, placements

c.execute("""CREATE TABLE tables(
    tableid INTEGER PRIMARY KEY AUTOINCREMENT,
    size INTEGER,
    tier TEXT,
    names TEXT,
    placements TEXT,
    tableurl TEXT,
    messageid INTEGER
)""")

c.execute("""CREATE TABLE updated(
    tableid INTEGER,
    rowids TEXT,
    colids TEXT,
    peakChanges TEXT,
    msgid INTEGER,
    tier TEXT
)""")

#c.execute("SELECT * from tables")
#tables = c.fetchall()
#for table in tables:
#    print(table)

##c.execute("DELETE from tables WHERE rowid = 2")

#c.execute("""SELECT * from tables WHERE tableid = ?""", (7,))
##c.execute("""SELECT * from updated""")
##tables = c.fetchall()
##for table in tables:
##    print(table)

c.execute("""ALTER TABLE tables
    ADD COLUMN authorid INTEGER DEFAULT 0
    """)

db.commit()

db.close()
