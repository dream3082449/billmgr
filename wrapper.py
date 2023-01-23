#!env python
import sys, json
import sqlite3
import uuid
import MySQLdb

con = None

mysql_params = {
    "host": "193.106.172.90",
    "port": 3306,
    "user": "DmitryK",
    "passwd": "dtpe,kbq",
    "db": "vmdaemon_db"
}

params = dict()
for e, p in enumerate(sys.argv):
	if e == 0:
		continue
	k, v = p.replace('--', '').split('=')
	params[k] =v
	
#conn = sqlite3.connect('queues.db')
#cursor = conn.cursor()
conn = MySQLdb.connect(**mysql_params)
cursor = conn.cursor()

# cursor.execute("""CREATE TABLE IF NOT EXISTS queue(
#     id INTEGER PRIMARY KEY,
#     request_id UUID,
#     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     on_process INTEGER DEFAULT 0,
#     is_done INTEGER DEFAULT 0,
#     params TEXT,
#     result TEXT,
#     response TEXT,
#     is_retry INTEGER DEFAULT 0);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS `queue` (
    `id` INT(11) NOT NULL,
    `request_id` BINARY(16) NOT NULL AUTO_INCREMENT,
    # taken from https://dev.mysql.com/blog-archive/storing-uuid-values-in-mysql-tables/
    `request_id_text` VARCHAR(36) GENERATED ALWAYS AS
    (INSERT(
      INSERT(
        INSERT(
          INSERT(HEX(request_id),9,0,'-'),
          14,0,'-'),
        19,0,'-'),
      24,0,'-')
    ) VIRTUAL,
    #
    `created` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    `on_process` INT(11) DEFAULT 0,
    `is_done` INT(11) DEFAULT 0,
    `params` TEXT DEFAULT NULL,
    `result` TEXT DEFAULT NULL,
    `response` TEXT DEFAULT NULL,
    `is_retry` INT(11) DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `request_id` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;""")

conn.commit()

# cursor.execute("""CREATE TABLE IF NOT EXISTS users(
#     id INTEGER PRIMARY KEY,
#     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     username TEXT,
#     project TEXT,
#     email TEXT);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS `users` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `created` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    `username` TEXT DEFAULT NULL,
    `project` TEXT DEFAULT NULL,
    `email` TEXT DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;""")
  
conn.commit()

# cursor.execute("""CREATE TABLE IF NOT EXISTS flavors(
#     id INTEGER PRIMARY KEY,
#     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     project_id TEXT,
#     flavor_id TEXT
#     instance_id TEXT);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS `flavors` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `created` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    `project_id` TEXT DEFAULT NULL,
    `flavor_id` TEXT DEFAULT NULL,
    `instance_id` TEXT DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;""")

conn.commit()

# cursor.execute("""CREATE TABLE IF NOT EXISTS instances(
#     id INTEGER PRIMARY KEY,
#     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     user_id INTEGER DEFAULT 0,
#     openstack_uuid TEXT,
#     project TEXT,
#     params TEXT);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS `instances` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `created` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    `user_id` INT(11) DEFAULT 0,
    `openstack_uuid` TEXT DEFAULT NULL,
    `project` TEXT DEFAULT NULL,
    `params` TEXT DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;""")

conn.commit()

# cursor.execute("""CREATE TABLE IF NOT EXISTS os_images(
#     id INTEGER PRIMARY KEY,
#     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     openstack_uuid TEXT,
#     openstack_name TEXT,
#     billing_name TEXT);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS `os_images` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `created` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    `openstack_uuid` TEXT DEFAULT NULL,
    `project` TEXT DEFAULT NULL,
    `params` TEXT DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;""")

conn.commit()

params['request_id'] = str(uuid.uuid1())

if not params.get("commandfile"):
    print("Database init")
    quit()
elif params['commandfile'] =='open':
	params['indent_id'] = str(uuid.uuid1())
else:
	params['indent_id'] = None
print(params['request_id'], params['indent_id'])

cursor.execute("""INSERT INTO queue (request_id, params) VALUES (?, ?);""", [params['request_id'], json.dumps(params)])
conn.commit() 

cursor.close()
