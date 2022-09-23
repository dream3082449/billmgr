#!env python
import sys, json
import sqlite3
import uuid

con = None

params = dict()
for e, p in enumerate(sys.argv):
	if e == 0:
		continue
	k, v = p.replace('--', '').split('=')
	params[k] =v
	
conn = sqlite3.connect('queues.db')
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS queue(
    id INTEGER PRIMARY KEY,
    request_id UUID,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    on_process INTEGER DEFAULT 0,
    is_done INTEGER DEFAULT 0,
    params TEXT,
    result TEXT);""")
conn.commit()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username TEXT,
    project TEXT,
    email TEXT);""")
    
conn.commit()

cursor.execute("""CREATE TABLE IF NOT EXISTS instances(
    id INTEGER PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER DEFAULT 0,
    openstack_uuid TEXT,
    project TEXT,
    params TEXT);""")
    
conn.commit()

params['request_id'] = str(uuid.uuid1())

if params['commandfile'] =='open':
	params['indent_id'] = str(uuid.uuid1())
else:
	params['indent_id'] = None
print(params['request_id'], params['indent_id'])

cursor.execute("""INSERT INTO queue (request_id, params) VALUES (?, ?);""", [params['request_id'], json.dumps(params)])
conn.commit() 


cursor.close()