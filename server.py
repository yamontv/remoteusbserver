"""This module realise remote USB server"""
import socket
import select
#mycodeincs
from radmin import RemoteAdmin
from phone import Phone


class RemoteUsbServer():
    """This is the main server class"""

    #maybe use socket.gethostname()
    _PHONE_HOST = '0.0.0.0'
    _PHONE_TCP_PORT = 65432
    _ADMIN_HOST = '0.0.0.0'
    _ADMIN_TCP_PORT = 65431

    def __init__(self, logger):
        self._logger = logger
        self._users_list = {}
        self._order_number = 0
        self._init_socket()

    def _loginfo(self, text):
        """This method log information msgs"""
        self._logger.info(text)

    def _logerror(self, text):
        """This method log critical msgs"""
        self._logger.critical(text)

    def _init_socket(self):
        """This method open listening TCP socket"""
        #create admin socket
        self._asock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._asock.bind((self._ADMIN_HOST, self._ADMIN_TCP_PORT))
        self._asock.listen()

        #create phone socket
        self._psock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._psock.bind((self._PHONE_HOST, self._PHONE_TCP_PORT))
        self._psock.listen()

    def run_once(self):
        """This method do the whole work"""
        # form socket list every time as list
        # could be moded in handlers
        socket_list = [self._asock, self._psock]
        for sock in self._users_list:
            socket_list.append(sock)

        infds, _, _ = select.select(socket_list, [], [], 1)

        for fds in infds:
            if fds is self._asock:
                sock, addr = fds.accept()
                self._loginfo('Admin connected from {}'.format(addr))
                RemoteAdmin(self._users_list, sock, addr)
                socket_list.append(sock)
                continue

            if fds is self._psock:
                sock, addr = fds.accept()
                self._loginfo('Phone connected from {}'.format(addr))
                Phone(self._order_number, self._users_list, sock, addr)
                self._order_number += 1
                if self._order_number > 999:
                    self._order_number = 0
                socket_list.append(sock)
                continue

            if fds in self._users_list:
                user = self._users_list[fds]
            else:
                #unknows -> close
                self._logerror("uknown socket in list")
                socket_list.remove(fds)
                fds.close()
                continue

            data = fds.recv(1024)
            if not data:
                #closed
                self._loginfo('{} disconnected'.format(user.get_addr()))
                fds.close()
                socket_list.remove(fds)
                del self._users_list[fds]
                user.close()
            else:
                user.handle_data(data)

        # check timeouts
        for sock in list(self._users_list):
            user = self._users_list[sock]
            user.check_timeout()

    def close(self):
        """This method destroy all server resources"""
        for sock in self._users_list:
            sock.close()
        self._asock.close()
        self._psock.close()
