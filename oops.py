#!env python
#!/usr/bin/python
import pymysql as MySQLdb
import sys
import openstack
#import mysql
import MySQLdb  


openstack.enable_logging(True, stream=sys.stdout)

class oops_helper(object):

    mysql_params = {
        "host": "localhost",
        "port": 3306,
        "user": "huy",
        "passwd": "pizda_djigurda",
#        "db": "billing"
    }

    mysql_conn = MySQLdb.connect(**mysql_params)

    # Initialize connection
    conn = openstack.connect(cloud='openstack')

    def get_or_create_user(self, username):
        response = self.conn.identity.find_user(username, ignore_missing=True)
        if response:
            return response
        else:
            return self.conn.identity.create_user(**{'name':username})


    def list_projects(conn):
        #print("List Projects:")

        for project in conn.identity.projects():
            project = list_p

    def list_services(conn):
        print("List Services:")

        for service in conn.identity.services():
            print(service)




