#!/usr/bin/env python3
import os, sys, time, json
import unittest
import sqlite3
import uuid

#from oops import oops_helper

from daemon import Daemon
PIDFILE = 'vmdaemon.pid'
LOGFILE = 'vmdaemon.log'
DBNAME = 'queues.db'

class VMDaemon(Daemon):
    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()

#    def __init__(self, *args, **kwargs):
#        super(VMDaemon, self).__init__(*args, **kwargs)
#        output = open(LOGFILE, 'w')
#        output.write('inited')
#        output.close()

    def get_queue(self):
        c = self.cur.execute("""
            SELECT params from queue where is_done=false and on_process=false order by created ASC LIMIT 1
            """).fetchall()
        return c

    def insert_or_update_user(self, params):
        c = self.cur.execute("""
            SELECT id from users where username=%s
            """, [params.get('username')]).fetchall()
        if not c:
            self.cur.execute("""
                INSERT INTO users (id, username, project, email) VALUES (?, ?, ?, ?);
                """, params)
        else:
            self.cur.execute("""
                UPDATE users set email=%s where username=%s
                """, [params[3], params[1]])
        return None

    def check_image_by_name(self, name):
        os_id = self.cur.execute("SELECT openstack_id from os_images WHERE billing_name=(?)", name).fetchone()
        if not os_id and self.cur.execute("SELECT COUNT(1) from os_images").fetchone() == 0:
            helper = oops_helper()
            for i in helper.list_images():
                c += 1
                self.cur.execute("""
                INSERT INTO os_images (openstack_uuid, openstack_name, billing_name) VALUES (?, ?, ?);
                """, [i[0], i[1], "bill_name_{0}".format(c)])
                os_id = i[0]
        elif not os_id:
            return None
        return os_id

    def ident_comand (self,command, params):
        helper = oops_helper()
        if command == "open":
            os_image_id = self.check_image_by_name(params.get('ostmpl'))
            if not os_image_id:
                return "Error: OS image not found"

            user_id, username, email = helper.product_id_to_username(params.get('user'))

            project_name = '{0}_project'.format(username)
            instance_name = '{0}_{1}'.format(username, params.get('user'))

            user_params = [user_id, username, project_name, email]
            self.insert_or_update_user(user_params)

            project = helper.get_or_create_project(project_name=project_name)

            attrs = {'username':username,
                'password':params.get('password'),
                'project_id': project.get('id'),
                'email':email}
            user = helper.get_or_create_user(**attrs)

            quotas_dict = {
                "cpu": params.get('cpu', None),
               #"hdd": params.get('hdd', None),
                "ram": params.get('ram', None),
                "instance": params.get('instance', None)
            }

            helper.update_project_quotes(project, quotas_dict)

            flavor_id = uuid.uuid1()
            flavor_params = {
                "name": "{0}_flavor_{1}".format(project_name, flavor_id)
                "ram":params.get('ram', None),
                "disk":params.get('disk', None),
                "vcpus":params.get('vcpus', None),
                "is_public": False,
            }

            flavor = helper.create_flavor(project, flavor_params)
            self.cur.execute("""
                INSERT INTO flavors (project_id, flavor_id) VALUES (?, ?); 
            """, [project.get('id'), flavor.get('id')])



            instance_params = {
                "os_image_id": os_image_id,
                "flavor_id": flavor.id,
                "password": params.get("password"),
                "instance_name": instance_name,
                "meta_name": params.get("user"),
            }
            helper.create_instance(project, instance_params)



#            ssh command '/opt/billmgr/open.sh --cpu=2 --hdd=20 --ippool=1 --ostempl=ubuntu-base
#            --password=aCEtOf6oLuPz --ram=4 --user=user11384 --vgpu1080=off' on root@10.10.84.135
#            cursor.execute("""INSERT INTO queue (on_process) VALUES (ID 1)""")
        elif command == "close":
            print(command)
#            cursor.execute("""INSERT INTO queue (on_process) VALUES (ID 2)""")
        elif command == "resume":
            print(command)
#            cursor.execute("""INSERT INTO queue (on_process) VALUES (ID 3)""")
        elif command == "setparam":
            print(command)
#            cursor.execute("""INSERT INTO queue (on_process) VALUES (ID 4)""")
        elif command == "suspend":
            print(command)
#            cursor.execute("""INSERT INTO queue (on_process) VALUES (ID 5)""")

        return 'Huy 22'

    def parse_data(self, data):
        r = json.loads(data[0][0])
        c = r.pop('commandfile')
        return (c, r)

    def run(self):
        time.sleep(0.3)
        output = open(LOGFILE, 'w')
        #TODO
        while True:
            data = self.get_queue()
            if data:
                for row in data:
                    #do something
                    command, params = self.parse_data(data)
                    output.write(f"%s %s" % (command, json.dumps(params)))
                    res = self.ident_comand(command, params)
                    output.write(res)

            else:
                time.sleep(10)
            #FOR DEBUG
            time.sleep(5)


        output.write('finished')
        output.close()


def control_daemon(action):
    os.system(" ".join((sys.executable, __file__, action)))


class TestDaemon(unittest.TestCase):
    testoutput = None

    def setUp(self):
        control_daemon('start')
        time.sleep(0.1)
        self.testoutput = open(LOGFILE)

    def test_daemon_can_start(self):
        assert os.path.exists(PIDFILE)
        assert self.testoutput.read() == 'inited'

    def test_daemon_can_stop(self):
        control_daemon('stop')
        time.sleep(0.1)
        assert os.path.exists(PIDFILE) is False
        assert self.testoutput.read() == 'inited'

    def test_daemon_can_finish(self):
        time.sleep(0.4)
        assert os.path.exists(PIDFILE) is False
        assert self.testoutput.read() == 'finished'

    def test_daemon_can_restart(self):
        assert os.path.exists(PIDFILE)
        pidfile = open(PIDFILE)
        pid1 = pidfile.read()
        pidfile.close()
        control_daemon('restart')
        time.sleep(0.1)
        assert os.path.exists(PIDFILE)
        pidfile = open(PIDFILE)
        pid2 = pidfile.read()
        pidfile.close()
        assert pid1 != pid2

    def tearDown(self):
        self.testoutput.close()
        if os.path.exists(PIDFILE):
            control_daemon('stop')
        time.sleep(0.05)
        os.system('rm {0}'.format(PIDFILE))


if __name__ == '__main__':
    if len(sys.argv) == 1:
        unittest.main()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ('start', 'stop', 'restart'):
            d = VMDaemon(PIDFILE, verbose=9)
            getattr(d, arg)()

