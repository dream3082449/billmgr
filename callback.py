#!env python
import sys, json, time
import sqlite3
import uuid

con = None

params = dict()
for e, p in enumerate(sys.argv):
	if e == 0:
		continue
	k, v = p.replace('--', '').split('=')
	params[k] =v

conn = sqlite3.connect('/opt/billmgr/queues.db')
cursor = conn.cursor()

while True:
	data = cursor.execute(
		"""SELECT result FROM queue WHERE request_id=(?) AND is_done=1 AND on_process=0;""",
		[params['request_id']]
		).fetchone()
	conn.commit()
	if data:
		print(data[0])
		break
	time.sleep(10)



