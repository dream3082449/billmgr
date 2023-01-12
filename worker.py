#!/usr/bin/env python3
import os, sys, time, json
import unittest
import sqlite3
import uuid

from oops import oops_helper

from daemon import Daemon
PIDFILE = 'vmdaemon.pid'
LOGFILE = 'vmdaemon.log'
DBNAME = 'queues.db'
DEBUG=True

class VMDaemon(Daemon):
#    def __init__(self, *args, **kwargs):
#        super(VMDaemon, self).__init__(*args, **kwargs)
#        output = open(LOGFILE, 'w')
#        output.write('inited')
#        output.close()

    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()

    def get_queue(self, on_process=False):
        c = self.cur.execute("""
            SELECT id, params, result from queue where is_done=false and on_process=? order by created ASC LIMIT 1
            """, [on_process,]).fetchall()
        return c

    def insert_or_update_user(self, params):
        ### params = [user_id, username, project_name, email]
        c = self.cur.execute("SELECT id from users where username=?", [params[1]]).fetchall()
        if not c:
            self.cur.execute("""
                INSERT INTO users (id, username, project, email) VALUES (?, ?, ?, ?);
                """, params)
        else:
            self.cur.execute("""
                UPDATE users set email=? where username=?
                """, [params[3], params[1]])
        self.conn.commit()
        return None

    def check_image_by_name(self, name):
        o = self.cur.execute("SELECT openstack_uuid from os_images WHERE billing_name = ?", [name,]).fetchone()
        if o:
            os_id = o[0]
        else:
            os_id = o
        c = self.cur.execute("SELECT COUNT(1) from os_images").fetchone()[0]
        if not os_id and c == 0:
            helper = oops_helper()
            for i in helper.list_images():
                c += 1
                self.cur.execute("""
                INSERT INTO os_images (openstack_uuid, openstack_name, billing_name) VALUES (?, ?, ?);
                """, [i[0], i[1], "bill_name_{0}".format(c)])
                os_id = i[0]
            self.conn.commit()
        elif not os_id:
            return None
        return os_id

    def ident_command (self, rid, command, params):
        helper = oops_helper()
        if command == "open":
            os_image_id = self.check_image_by_name(params.get('ostempl'))
            if not os_image_id:
                return "Error: OS image not found"
            product_id = params.get('user').strip('user')
            user_id, username, email = helper.product_id_to_username(product_id)

            project_name = '{0}_project'.format(username)
            instance_name = '{0}_{1}'.format(username, product_id)

            user_params = [user_id, username, project_name, email]

            project = helper.get_or_create_project(project_name=project_name)

            #save to local DB
            self.insert_or_update_user(user_params) 

            attrs = {'username':username,
                'password':params.get('password'),
                'project_id': project.get('id'),
                'email':email}
            user = helper.get_or_create_user(**attrs)

            quotas_dict = {
                "cores": int(params.get('cpu', 0)),
                "hdd": int(params.get('hdd', 0)),
                "ram": int(params.get('ram', 0)),
            }

            helper.update_project_quotas(project, quotas_dict)

            flavor_id = uuid.uuid1()
            flavor_params = {
                "name": "{0}_flavor_{1}".format(project_name, flavor_id),
                "ram": int(params.get('ram', 0)),
                "disk": int(params.get('hdd', 0)),
                "vcpus": int(params.get('cpu', 1)),
                "is_public": False,
            }

            flavor = helper.create_flavor(project, flavor_params)
            self.cur.execute("""
                INSERT INTO flavors (project_id, flavor_id) VALUES (?, ?); 
            """, [project.get('id'), flavor.get('id')])
            self.conn.commit()


            instance_params = {
                "os_image_id": os_image_id,
                "flavor_id": flavor.id,
                "password": params.get("password"),
                "instance_name": instance_name,
                "meta_name": params.get("user"),
                'user_id': user_id
            }
            ii = helper.create_instance(project, instance_params)
            instance = ii.to_dict()
            j_instance = json.dumps(instance)
            self.cur.execute("UPDATE queue SET result=? WHERE id=?", [j_instance, rid])
            self.cur.execute("""
                INSERT INTO instances (user_id, openstack_uuid, project, params) VALUES (?, ?, ?, ?)
            """, [user_id, instance.get('id'), project.get('id'), j_instance])

            return j_instance


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

        return 'Command does not exist'

    def check_command_readiness(self, rid, command, params, result):
        if command == "open":
            print(result)
        elif command == "close":
            pass
        elif command == "resume":
            pass
        elif command == "setparam":
            pass
        elif command == "suspend":
            pass
        return 'Command not exists on readiness'

    def prepare_data(self, data, set_on_process=False):
        rid = data[0]
        if set_on_process:
            self.cur.execute("UPDATE queue SET on_process=1 where id=?", [str(rid)])
        r = json.loads(data[1])
        c = r.pop('commandfile')
        result = data[2]
        return (rid, c, r, result)

    def run(self):
        time.sleep(0.3)
        output = open(LOGFILE, 'w')
        #TODO
        while True:
            for row in self.get_queue():
                #do something
                rid, command, params, _ = self.prepare_data(row, set_on_process=True)
                output.write(f"%s %s" % (command, json.dumps(params)))
                res = self.ident_command(rid, command, params)
                output.write(res)

            for row in self.get_queue(on_process=True):
                rid, command, params, result = self.prepare_data(row, set_on_process=False)
                output.write(f"%s %s" % (command, json.dumps(params)))
                res = self.check_command_readiness(rid, command, params, result)
                output.write(res)

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
            d = VMDaemon(pidfile=PIDFILE, verbose=9)
            getattr(d, arg)()

