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

    def product_id_to_username(self, product_id, username_only=True):
        query = 'select a.id, a.name from item i left join account a on i.account=a.id where i.id = %s'
        self.mysql_cursor.execute(query, [product_id,])
        try:
            user_id, username = self.mysql_cursor.fetchone()
        except Exception:
            return None

        if username_only:
            return username
        else:
            return (user_id, username)


    def get_or_create_user(self, username):
        response = self.conn.identity.find_user(username, ignore_missing=True)
        if response:
            return response
        else:
            return self.conn.identity.create_user(**{'name':username})


    def get_or_create_project(conn):
        #print("List Projects:")

        for project in conn.identity.projects():
            project = list_p

    def get_or_create_flavor(conn, project):
        pass

    def get_free_hive_gpu(conn):
        pass

    def list_services(conn):
        print("List Services:")

        for service in conn.identity.services():
            print(service)

    def create_instance(conn, params):
        #product_id_to_username()
        #get_or_create_project()
        #get_or_create_flavor()
        #get_free_hive_gpu()

        #logic for creating instance in project with flavor and hive gpu
        pass

    def reomve_instance(conn, params):
        pass

    def change_flavor(conn, params):
        pass

