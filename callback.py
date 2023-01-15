#!env python
import sys, json, time
import sqlite3
import uuid
import logging


LOGFILE = './callback.log'
DEBUG=True
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    filename=LOGFILE,
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG
)


con = None

params = dict()
for e, p in enumerate(sys.argv):
	if e == 0:
		continue
	k, v = p.replace('--', '').split('=')
	params[k] =v

conn = sqlite3.connect('/opt/billmgr/queues.db')
cursor = conn.cursor()

logging.info("Run callback with request_id={0}".format(params['request_id']))

while True:
	data = cursor.execute(
		"""SELECT response FROM queue WHERE request_id=(?) AND is_done=1 AND on_process=0;""",
		[params['request_id']]
		).fetchone()
	conn.commit()
	if data:
		logger.info('Successful response to billing: '.format(data[0]))
		print(data[0])
		break
	time.sleep(5)



