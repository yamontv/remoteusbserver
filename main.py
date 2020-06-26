"""Application convert"""
import logging
import os
import signal
from threading import Event
import coloredlogs
import daemon
import daemon.pidfile
#mycodeincs
from server import RemoteUsbServer

_VERSION = "0.1"


def input_yes_no(question, default=None):
    """This function take only yes no answer"""
    ret = False
    while ret != 'Y' and ret != 'N':
        try:
            if default is not None:
                if default:
                    dft = 'y'
                else:
                    dft = 'n'
                ans = input("{} [y/n]'{}': ".format(question, dft))
                if not ans:
                    return default
                ret = ans.upper()
            else:
                ret = input("{} [y/n]: ".format(question)).upper()
        except KeyboardInterrupt:
            print('\n')
            exit(0)

    if ret == 'Y':
        return True
    else:
        return False


class MainAPP():
    """This is the app convert for server"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stop_request = Event()

    def sigint_handler(self, _signum, _frame):
        """SIGINT handler"""
        self.stop_request.set()

    def daemon_work(self):
        """work as daemon"""
        #setup logger to file
        hdlr = logging.FileHandler('log.log', mode='w')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)

        server = RemoteUsbServer(self.logger)
        self.logger.info("Started")

        while not self.stop_request.isSet():
            server.run_once()

        server.close()
        self.logger.info("Stopped")

    def daemonise(self):
        """daemonise application"""
        here = os.path.dirname(os.path.abspath(__file__))
        out = open('std.log', 'w+')

        context = daemon.DaemonContext(
            working_directory=here,
            stdout=out,
            stderr=out,
            pidfile=daemon.pidfile.PIDLockFile('pid.pid'))

        context.signal_map = {
            signal.SIGTERM: self.sigint_handler,
        }

        context.open()
        with context:
            self.daemon_work()

    def direct(self):
        """direct run of application"""
        coloredlogs.install(
            level='INFO',
            fmt='%(asctime)s,%(msecs)03d %(message)s',
            datefmt='%H:%M:%S',
            logger=self.logger)

        server = RemoteUsbServer(self.logger)
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.logger.info("Started")

        while not self.stop_request.isSet():
            server.run_once()

        server.close()
        self.logger.info("Stopped")

    def start(self):
        """start application"""
        print('Welcome to RemoteUsbServer v{}'.format(_VERSION))
        do_daemon = input_yes_no("Daemonise?", False)

        if do_daemon:
            self.daemonise()
        else:
            self.direct()


if __name__ == "__main__":
    APP = MainAPP()
    APP.start()
