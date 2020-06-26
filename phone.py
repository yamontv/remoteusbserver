"""This module realise remote Phone class"""
from os import urandom
from time import time
from rc4 import RC4

_CRYPTO_KEY = [
    0x05,
    0x27,
    0x06,
    0x9e,
    0x9e,
    0x44,
    0xeb,
    0x44,
    0xa7,
    0x48,
    0x47,
    0xbd,
    0xca,
    0xc9,
    0xae,
    0x2d,
    0xf9,
    0xf2,
    0x75,
    0x87,
    0xc7,
    0x08,
    0x1e,
    0x1e,
]


class Phone():
    """This is the phone class"""
    _TIMEOUT = 10
    _AUTH_LEN = 512
    _NONCE_LEN = 4
    _SET_NUMBER_CMD = b'\xff'
    _SET_SPEED_CMD = b'\xfe'

    def __init__(self, number, user_list, sock, addr):
        self._user_list = user_list
        self._sock = sock
        self._addr = addr
        self._user_list[sock] = self
        self._number = number
        self._speed = 57600

        #generate random data to check client
        self._auth_data = bytearray(urandom(self._AUTH_LEN))

        #generate nonce
        nonce = bytearray(urandom(self._NONCE_LEN))
        self._cipher_tx = RC4(nonce=bytearray(_CRYPTO_KEY) + nonce)
        #invert nonce for rx
        nonce_inv = []
        for _, val in enumerate(nonce):
            nonce_inv.append(val ^ 0xFF)
        self._cipher_rx = RC4(
            nonce=bytearray(_CRYPTO_KEY) + bytearray(nonce_inv))

        self._timeout = time()
        self._wait_auth = True

        self.remote_user = None

        #send nonce with auth
        self._sock.send(nonce + self._cipher_tx.crypt(self._auth_data))

    def is_admin(self):
        """This method determine user type"""
        return False

    def ready(self):
        """This method show if we are ready"""
        if self._wait_auth:
            return False
        return True

    def get_number(self):
        """number getter"""
        return self._number

    def set_number(self):
        """Set number"""
        self._send(self._SET_NUMBER_CMD +
                   self._number.to_bytes(1, byteorder='big'))

    def get_speed(self):
        """speed getter"""
        return self._speed

    def get_addr(self):
        """speed getter"""
        return self._addr

    def set_speed(self, speed):
        """set uart speed"""
        self._speed = speed
        self._send(self._SET_SPEED_CMD + speed.to_bytes(3, byteorder='big'))

    def force_close(self):
        """force close"""
        self.remote_user = None
        del self._user_list[self._sock]
        self._sock.close()

    def check_timeout(self):
        """Check auth timeout"""
        if self._timeout is None:
            return
        if time() - self._timeout > self._TIMEOUT:
            self.force_close()

    def handle_data(self, data):
        """This method handle data"""
        if self._wait_auth:
            if len(data) != self._AUTH_LEN:
                self.force_close()
                return
            data = list(self._cipher_rx.crypt(data))
            authl = list(self._auth_data)
            if data == authl:
                self._wait_auth = False
                self._timeout = None
                self.set_number()
            else:
                self.force_close()
        elif self.remote_user:
            self.remote_user.send(self._cipher_rx.crypt(data))

    def _sends(self, datastr):
        """This method send string"""
        self._send(datastr.encode('utf-8'))

    def _send(self, data):
        """This method send bytes"""
        self._sock.send(self._cipher_tx.crypt(data))

    def send(self, data):
        """This public method send bytes from phones"""
        if not self.remote_user:
            return

        self._send(data)

    def close(self):
        """close all resources"""
        if self.remote_user:
            self.remote_user.send(
                '***Remote phone close connection***\r\n'.encode('utf-8'))
            self.remote_user.remote_user = None
