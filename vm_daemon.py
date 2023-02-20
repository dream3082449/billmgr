#!env python3
import sys
import os
import time
import argparse
import logging
import daemon
from daemon import pidfile

debug_p = False


class VMDaemon():

    def __init__(self, logger):
        self.conn = sqlite3.connect('queues.db')
        self.cur = conn.cursor()
        self.logger = logger
        self.helper = oops_helper()

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
                logging.error("OS image not found for Instance {0} is ".format(params.get('user')))
                return None
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
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('id'),]).fetchone()
            if data:
                self.delete_instance(data[0])
                self.cur.execute("DELETE from instances where openstack_uuid=?", [data[0]])
                self.conn.commit()
            else:
                logging.warning("Instance for product_id {0} not found, so can`t be deleted".format(params.get('id')))
            return None

        elif command == "suspend":
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('id'),]).fetchone()
            if data:
                i_status, _ = self.helper.get_instance_status(data[0])
                if i_status != 'ACTIVE':
                    logging.warning("The instance status for product_id {0} is not 'active' , so it cannot be suspended".format(params.get('user')))
                    return None
                self.helper.suspend_instance(data[0])
                logging.info("Instance {0} suspended".format(data[0]))
            else:
                logging.warning("Instance for product_id {0} not found, so cannot be suspended".format(params.get('id')))
            return None

        elif command == "resume":
            data = self.cur.execute("SELECT openstack_uuid FROM instances WHERE user_id=?", [params.get('id'),]).fetchone()
            if data:
                i_status, _ = self.helper.get_instance_status(data[0])
                if i_status != 'SUSPENDED':
                    logging.warning("The instance status for product_id {0} is not 'SUSPENDED' , so it cannot resumed".format(params.get('user')))
                    return None
                self.helper.resume_instance(data[0])
                logging.info("Instance {0} resumed".format(data[0]))
            else:
                logging.warning("Instance for product_id {0} not found, so cannot be resumed".format(params.get('id')))
            return None

        ### TODO
        elif command == "setparam":
            if params.get('change_volume_size', False):
                pass
            elif params.get('change_cpu', False):
                pass
            elif params.get('change_ram', False):
                pass
        ### END TODO

        return 'Command does not exist'

    def delete_instance(self, instance_id):
        self.helper.remove_instance(instance_id)
        logger.warning("Instance {0} was DELETED".format(instance_id))
        return True

    def check_command_readiness(self, rid, command, params, result):
        if command == "open":
            res = json.loads(result)
            if not res:
                logger.error('Error on request_id={0} : no result found. restart task'.format(params.get('request_id')))
                self.cur.execute("UPDATE queue SET on_process=0 WHERE id=?", [rid,])
                self.conn.commit()
                return None
            instance_id = res.get('id')
            instance_status, instance = self.helper.get_instance_status(instance_id)
            if instance_status == 'ACTIVE':
                logger.info("Instance {0} is ACTIVE".format(instance_id))

                response_for_bill = "OK --id={0} --username={1} --password={2} --ip-addr={3} --server_login={4}".format(
                    params.get('user'),
                    params.get('user'),
                    params.get('password'),
                    instance['addresses']['provider'][0]['addr'],
                    'root'
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
                    logger.info("Set queue task {0} param to recreate instance".format(rid))
                self.conn.commit()

                logger.error("Instance {0} have status {1}. Try to recreate it".format(instance_id, instance_status))

                self.delete_instance(instance_id)
                #run ident_command to create the new one
                self.ident_command(rid, command, params)

            else:
                logging.warning("Instance {0} have status {1}".format(instance_id, instance_status))
            return None

        elif command == "close":
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            self.conn.commit()
            return None

        elif command == "resume":
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            self.conn.commit()
            return None

        elif command == "suspend":
            result = json.dumps({"status":"DONE"})
            response_for_bill = "OK"
            self.cur.execute("UPDATE queue SET is_done=1, on_process=0, result=?, response=? WHERE id=?", 
                [result, response_for_bill, rid]
            )
            self.conn.commit()
            return None

        ### TODO
        elif command == "setparam":
            pass

        ### END TODO

        return 'Command not exists on readiness'

    def prepare_data(self, data, set_on_process=False):
        rid = data[0]
        if set_on_process:
            self.cur.execute("UPDATE queue SET on_process=1 where id=?", [rid])
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


def runner(logf):
    ### This does the "work" of the daemon

    logger = logging.getLogger('vm_daemon')
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(logf)
    fh.setLevel(logging.INFO)

    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)

    fh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.info("Run VMDaemon")
    vmd = VMDaemon(logger)
    vmd.run()


def start_daemon(pidf, logf):
    ### This launches the daemon in its context

    global debug_p

    if debug_p:
        print("vm_daemon: entered run()")
        print("vm_daemon: pidf = {}    logf = {}".format(pidf, logf))
        print("vm_daemon: about to start daemonization")

    ### XXX pidfile is a context
    with daemon.DaemonContext(
        working_directory=os.getcwd(),
        umask=0o002,
        pidfile=pidfile.TimeoutPIDLockFile(pidf),
        ) as context:
        runner(logf)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BillManager to OpenStack integration daemon")
    parser.add_argument('-p', '--pid-file', default='/var/run/eg_daemon.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/eg_daemon.log')

    args = parser.parse_args()
    
    start_daemon(pidf=args.pid_file, logf=args.log_file)
