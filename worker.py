#!/usr/bin/env python3
import os, sys, time, json
import unittest
import sqlite3
import uuid
import logging

from oops import oops_helper

from daemon import Daemon
PIDFILE = './vmdaemon.pid'
LOGFILE = './vmdaemon.log'
DBNAME = 'queues.db'
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
logging.info("Run VMDaemon")

class VMDaemon(Daemon):
#    def __init__(self, *args, **kwargs):
#        super(VMDaemon, self).__init__(*args, **kwargs)
#        output = open(LOGFILE, 'w')
#        output.write('inited')
#        output.close()

    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()

    helper = oops_helper()

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
            for i in self.helper.list_images():
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
        if command == "open":
            os_image_id = self.check_image_by_name(params.get('ostempl'))
            if not os_image_id:
                return "Error: OS image not found"
            product_id = params.get('user').strip('user')
            user_id, username, email = self.helper.product_id_to_username(product_id)

            project_name = '{0}_project'.format(username)
            instance_name = '{0}_{1}'.format(username, product_id)

            user_params = [user_id, username, project_name, email]

            project = self.helper.get_or_create_project(project_name=project_name)

            #save to local DB
            self.insert_or_update_user(user_params) 

            attrs = {'username':username,
                'password':params.get('password'),
                'project_id': project.get('id'),
                'email':email}
            user = self.helper.get_or_create_user(**attrs)

            quotas_dict = {
                "cores": int(params.get('cpu', 0)),
                "hdd": int(params.get('hdd', 0)),
                "ram": int(params.get('ram', 0)),
            }

            self.helper.update_project_quotas(project, quotas_dict)

            flavor_id = uuid.uuid1()
            flavor_params = {
                "name": "{0}_flavor_{1}".format(project_name, flavor_id),
                "ram": int(params.get('ram', 0)),
                "disk": int(params.get('hdd', 0)),
                "vcpus": int(params.get('cpu', 1)),
                "is_public": False,
            }

            flavor = self.helper.create_flavor(project, flavor_params)
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
            ii = self.helper.create_instance(project, instance_params)

            instance = ii.to_dict()
            j_instance = json.dumps(instance)

            logging.info("Instance {0} is CREATED".format(instance.get('id')))

            self.cur.execute("UPDATE queue SET result=? WHERE id=?", [j_instance, rid])
            self.cur.execute("""
                INSERT INTO instances (user_id, openstack_uuid, project, params) VALUES (?, ?, ?, ?)
            """, [params.get('user'), instance.get('id'), project.get('id'), j_instance])
            self.conn.commit()
            return j_instance

#            ssh command '/opt/billmgr/open.sh --cpu=2 --hdd=20 --ippool=1 --ostempl=ubuntu-base
#            --password=aCEtOf6oLuPz --ram=4 --user=user11384 --vgpu1080=off' on root@10.10.84.135
        elif command == "close":
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('user'),]).fetchone()
            if data:
                self.delete_instance(data[0])
            else:
                logging.warning("Instance for product_id {0} not found, so can`t be deleted".format(params.get('user')))
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            return None

        elif command == "suspend":
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('user'),]).fetchone()
            if data:
                i_status, _ = self.helper.get_instance_status(data[0])
                if i_status != 'ACTIVE':
                    logging.warning("The instance status for product_id {0} is not 'active' , so it cannot be suspended".format(params.get('user')))
                    return None
                self.suspend_instance(data[0])
                logging.info("Instance {0} suspended".format(data[0]))
            else:
                logging.warning("Instance for product_id {0} not found, so cannot be suspended".format(params.get('user')))
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            return None

        elif command == "resume":
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('user'),]).fetchone()
            if data:
                i_status, _ = self.helper.get_instance_status(data[0])
                if i_status != 'PAUSED':
                    logging.warning("The instance status for product_id {0} is not 'PAUSED' , so it cannot resumed".format(params.get('user')))
                    return None
                self.suspend_instance(data[0])
                logging.info("Instance {0} resumed".format(data[0]))
            else:
                logging.warning("Instance for product_id {0} not found, so cannot be resumed".format(params.get('user')))
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            return None

        elif command == "setparam":


            print(command)


        return 'Command does not exist'

    def delete_instance(self, instance_id):
        self.helper.remove_instance(instance_id)
        logging.warning("Instance {0} was DELETED".format(instance_id))
        return True

    def check_command_readiness(self, rid, command, params, result):
        if command == "open":
            res = json.loads(result)
            if not res:
                logging.error('Error on request_id={0} : no result found. restart task'.format(params.get('request_id')))
                self.cur.execute("UPDATE queue SET on_process=0 WHERE id=?", [rid,])
                self.conn.commit()
                return None
            instance_id = res.get('id')
            instance_status, instance = self.helper.get_instance_status(instance_id)
            if instance_status == 'ACTIVE':
                logging.info("Instance {0} is ACTIVE".format(instance_id))

                response_for_bill = "OK --id={0} --username={1} --password={2} --ip-addr={3}".format(
                    params.get('user'),
                    'root',
                    params.get('password'),
                    instance['addresses']['provider'][0]['addr']
                )
                self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                        [json.dumps(instance), response_for_bill, rid]
                    )
                self.cur.execute("""
                        UPDATE instances SET params=? WHERE openstack_uuid=?
                    """, [json.dumps(instance), instance.get('id')])
                self.conn.commit()
            elif instance_status == 'ERROR':
                is_retry = bool(self.cur.execute("SELECT is_retry FROM queue WHERE id=?", [rid,]).fetchone()[0])
                if is_retry:
                    self.delete_instance(instance_id)
                    response_for_bill = "ERROR instance creation is broken"
                    self.cur.execute("UPDATE queue SET response=? WHERE id=?", [response_for_bill, rid])
                else:
                    self.cur.execute("UPDATE queue SET is_retry=1 WHERE id=?", [rid,])
                    logging.info("Set queue task {0} param to recreate instance".format(rid))
                self.conn.commit()

                logging.error("Instance {0} have status {1}. Try to recreate it".format(instance_id, instance_status))

                self.delete_instance(instance_id)
                #run ident_command to create the new one
                self.ident_command(rid, command, params)

            else:
                logging.warning("Instance {0} have status {1}".format(instance_id, instance_status))
            return None

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
        result = data[2] if data[2] else '{}'
        return (rid, c, r, result)

    def run(self):
        time.sleep(0.3)
        while True:
            for row in self.get_queue():
                rid, command, params, _ = self.prepare_data(row, set_on_process=True)
                logging.info(f"%s %s" % (command, json.dumps(params)))
                self.ident_command(rid, command, params)
                logging.info("Command %s with params %s on process." % (command, json.dumps(params)))

            for row in self.get_queue(on_process=True):
                rid, command, params, result = self.prepare_data(row)
                logging.info(f"%s %s" % (command, json.dumps(params)))
                self.check_command_readiness(rid, command, params, result)
                logging.info("Command %s is DONE with result %s" % (command, result))

            #FOR DEBUG
            time.sleep(5)


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

