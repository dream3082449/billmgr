#! /bin/env python3
import sys, json, time
import configparser
import MySQLdb
import uuid
import logging

path = "/etc/vm_daemon/settings.ini"
config = configparser.ConfigParser()
config.read(path)

LOGFILE = config.get("defaults", "log_file")
DEBUG = True
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    filename=LOGFILE,
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG
)


params = dict()
for e, p in enumerate(sys.argv):
    if e == 0:
        continue
    k, v = p.replace('--', '').split('=')
    params[k] = v

# conn = sqlite3.connect('/opt/billmgr/queues.db')
conn = MySQLdb.connect(
            host=config.get('MainDB', 'host'),
            port=int(config.get('MainDB', 'port')),
            user=config.get('MainDB', 'user'),
            password=config.get('MainDB', 'password'),
            db=config.get('MainDB', 'db_name')
        )cursor = conn.cursor()

logging.info("Run callback with request_id={0}".format(params['request_id']))

while True:
    #    data = cursor.execute(
    #        """SELECT response FROM vmdaemon_db.queue WHERE request_id=(?) AND is_done=1 AND on_process=0;""",
    #         [params['request_id']]
    #        ).fetchone()
    cursor.execute(
        """SELECT response FROM vmdaemon_db.queue WHERE request_id=(%s) AND is_done=1 AND on_process=0;""",
        [params['request_id']]
    )
    data = cursor.fetchone()
    conn.commit()
    if data:
        logger.info('Successful response to billing: '.format(data[0]))
        print(data[0])
        break
    time.sleep(5)
