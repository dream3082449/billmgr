#!env python3
import sys
import openstack
import MySQLdb  


openstack.enable_logging(True, stream=sys.stdout)

class oops_helper(object):

    mysql_params = {
        "host": "10.10.84.186",
        "port": 3306,
        "user": "os_user",
        "passwd": "dtpe,kbq",
        "db": "billmgr"
    }

    mysql_conn = MySQLdb.connect(**mysql_params)
    mysql_cursor = mysql_conn.cursor()

    # Initialize connection
    conn = openstack.connect(cloud='openstack')

    def product_id_to_username(self, product_id, username_only=False):
        query = 'select a.id, a.name, a.email from item i left join account a on i.account=a.id where i.id = %s'
        self.mysql_cursor.execute(query, [product_id,])
        try:
            user_id, username, email = self.mysql_cursor.fetchone()
        except Exception:
            return None

        if username_only:
            return username
        else:
            return (user_id, username, email)


    def get_or_create_user(self, username, password, project_id, email):
        response = self.conn.identity.find_user(username, ignore_missing=True)
        if response:
            return response
        else:
            attrs = {
                'name':username,
                'password':password,
                'default_project_id': project_id,
                'email': email,
                'is_enabled': True
                }
            return self.conn.identity.create_user(**attrs)


    def get_or_create_project(conn, project_name):
        resp = self.conn.identity.find_project(project_name)
        if resp:
            return resp
        else:
            attrs = {
            'is_enabled': True,
            'name': project_name
            }
            return self.conn.create_project(**attrs)

    def update_project_quotes(self, project, params):
        project_id = project.get('id')
        current_quotas = self.conn.get_compute_quotas(project_id)

        if current_quotas.get('instances') < params.get('instance'):
            instances = params.get('instance')
        else:
            instances = current_quotas.get('instances') + params.get('instance')

        if current_quotas.get('cores') < params.get('cpu'):
            cores = params.get('instance')
        else:
            cores = current_quotas.get('cores') + params.get('cpu')

        new_ram = params.get('ram') * 1024 # bump Gigabytes to megabytes for OpenStack cli

        if current_quotas.get('ram') < new_ram:
            ram = new_ram
        else:
            ram = current_quotas.get('ram') + new_ram

        p = {
            "cores": cores,
            "instances": instances,
            "ram": ram,
        }
        self.conn.set_compute_quotas(project_id, **p)
        return True

    def create_flavor(self, project, params):
        flavor = self.conn.create_flavor(**params)
        conn.add_flavor_access(flavor.get('id'), project.get('id'))
        return flavor

    def get_free_hive_gpu(conn):
        pass

    def list_services(conn):
        print("List Services:")

        for service in conn.identity.services():
            print(service)

    def create_instance(self, params):
        image = conn.find_image(params.get("ostmpl"))
        p = {"server" : {
            "adminPass": params.get("password"),
#            "accessIPv4": "1.2.3.4",
#            "accessIPv6": "80fe::",
            "name" : "new-server-test",
            "imageRef" : "70a599e0-31e7-49b7-b260-868f441e862b",
            "flavorRef" : "6",
            "OS-DCF:diskConfig": "AUTO",
            "metadata" : {
                "My Server Name" : "Apache1"
            },
            "security_groups": [
                {
                    "name": "default"
                }
            ],
            "user_data" : "IyEvYmluL2Jhc2gKL2Jpbi9zdQplY2hvICJJIGFtIGluIHlvdSEiCg==",
            "networks": "auto",
#            "host": "openstack-node-01",
#            "hypervisor_hostname": "openstack-node-01"
            }
        }

        #logic for creating instance in project with flavor and hive gpu
        pass

    def reomve_instance(conn, params):
        pass

    def change_flavor(conn, params):
        pass

