"""This module realise RC4 cipher"""
from hashlib import sha256


class RC4():
    """This is the RC4 cipher class"""

    def __init__(self, nonce=None, key=None):
        """Create RC4 object with the storage elements allocated."""
        self._sbox = list(range(256))
        self._xind = 0
        self._yind = 0

        if nonce:
            #calculate key from nonce
            digest = sha256()
            digest.update(nonce)
            key = digest.digest()

        ind2 = 0
        for ind in range(256):
            ind2 = (ind2 + self._sbox[ind] + key[ind % len(key)]) % 256
            # Swap elements in S using a nice Python trick.
            self._sbox[ind], self._sbox[ind2] = self._sbox[ind2], self._sbox[
                ind]

    def generate_keystream(self, stream_length=1):
        """Generate and return a list with stream_length keystream bytes."""
        keystream = []

        for _ in range(stream_length):
            self._xind = (self._xind + 1) % 256
            self._yind = (self._yind + self._sbox[self._xind]) % 256
            # Swap elements in S using a nice Python trick.
            self._sbox[self._xind], self._sbox[self._yind] = self._sbox[
                self._yind], self._sbox[self._xind]

            keystream.append(
                self._sbox[(self._sbox[self._xind] + self._sbox[self._yind]) %
                           256])

        return keystream

    def crypt(self, data):
        """xor keystream to bytearray"""
        ldata = list(data)
        keystream = self.generate_keystream(len(data))
        for ind in range(len(data)):
            ldata[ind] ^= keystream[ind]

        return bytearray(ldata)
