#!/usr/bin/env python3
import os, sys, time
import unittest
import sqlite3

from daemon import Daemon
PIDFILE = 'vmdaemon.pid'
LOGFILE = 'vmdaemon.log'
DBNAME = 'queues.db'

class VMDaemon(Daemon):
    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()

    def __init__(self, *args, **kwargs):
        super(VMDaemon, self).__init__(*args, **kwargs)
        output = open(LOGFILE, 'w')
        output.write('inited')
        output.close()

    def get_queue(self):
        # c = self.cur.execute("""
        #     SELECT * from queue where is_done=false order by created ASC LIMIT 1
        #     """).fetchall()
        return None

    def ident_comand (self,command ):

        if command == "open":
            print(command)
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
        parsed_data = 'Huy'
        return parsed_data

    def run(self):
        time.sleep(0.3)
        output = open(LOGFILE, 'w')
        #TODO
        while True:
            data = self.get_queue()
            if data:
                for row in data:
                    #do something
                    p = self.parse_data(data)
                    output.write(p)
                    res = self.ident_comand(p)
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
            d = VMDaemon(PIDFILE, verbose=0)
            getattr(d, arg)()

