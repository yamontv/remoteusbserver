"""This module realise remote Admin class"""

IAC = bytes([255])  # "Interpret As Command"
DO = bytes([253])
DONT = bytes([254])
WILL = bytes([251])
WONT = bytes([252])

ECHO = bytes([1])  # echo
SGA = bytes([3])  # suppress go ahead
NOP = bytes([241])  # No Operation
SB = bytes([250])  # Subnegotiation Begin
NAWS = bytes([31])  # window size

# Make the telnet client understand we will echo characters so it
# should not do it locally. We don't tell the client to run linemode,
# because we want to handle line editing and tab completion and other
# stuff that requires char-by-char support
RAW_MODE = IAC + DO + ECHO + IAC + DO + NAWS + IAC + WILL + ECHO + IAC + WILL + SGA
# do oposite
NORMAL_MODE = IAC + DONT + ECHO + IAC + DONT + NAWS + IAC + WONT + ECHO + IAC + WONT + SGA


def iac_protect(data):
    """This function protect IACs in data"""
    out = b''

    for bte in data:
        if bte == IAC[0]:
            out += IAC
        elif bte == 10:
            out += bytes([13])
        out += bytes([bte])

    return out


def iac_filter(data):
    """This function filter IACs in data"""
    out = b''
    i = 0

    while i < len(data):
        if data[i] != IAC[0]:
            # We map \r\n ==> \r for pragmatic reasons.
            # Many client implementations send \r\n when
            # the user hits the CarriageReturn key.
            # See RFC 1123 3.3.1 Telnet End-of-Line Convention.
            if data[i] == ord('\r') and i + 1 < len(data) and data[
                    i + 1] == ord('\n'):
                i += 1

            out += bytes([data[i]])

            i += 1

            continue

        if i + 1 >= len(data):
            break

        if data[i + 1] == NOP[0]:
            #Ignore? (putty keepalive, etc.)
            i += 2
            continue

        if data[i + 1] == IAC[0]:
            #Literal IAC? (emacs M-DEL)
            i += 2
            continue

        # TELOPT_NAWS support!
        if i + 2 >= len(data):
            # Only the beginning of the IAC is in the
            # buffer we were asked to process, we can't
            # process this char
            break

        # IAC -> SB -> TELOPT_NAWS -> 4-byte -> IAC -> SE
        if data[i + 1] == SB[0] and data[i + 2] == NAWS[0]:
            i += 9
            continue

        # skip 3-byte IAC non-SB cmd */
        i += 3

    return out


class RemoteAdmin():
    """This is the remote admin class"""
    _SPEED_MODES = [9600, 19200, 33600, 57600, 115200]

    _DEFAULT_SPEED = 3  #57600

    def __init__(self, user_list, sock, addr):
        self._user_list = user_list
        self._sock = sock
        self._addr = addr
        self._user_list[sock] = self
        self.remote_user = None
        self._menu_mode = True
        self._enter_menu_mode()

    def is_admin(self):
        """This method determine user type"""
        return True

    def check_timeout(self):
        """This method do nothing"""

    def get_addr(self):
        """speed getter"""
        return self._addr

    def _enter_menu_mode(self):
        self._menu_mode = True
        self._menu_out()
        self._send(NORMAL_MODE)

    def _enter_connect_mode(self):
        self._menu_mode = False
        self._sends(
            "You are connected to phone. To show menu press 'ctrl + ['\r\n")
        self._send(RAW_MODE)

    def _get_phones(self):
        # gather phones
        phones = []
        for idx in self._user_list:
            user = self._user_list[idx]
            if user.is_admin():
                continue
            if user.ready():
                phones.append(user)
        return phones

    def _menu_out(self):
        out = '\r\n\r\n\r\n\tRemote Terminal Server\r\n'
        out += '------------------------------------------\r\n'

        if self.remote_user:
            out += 'Connected to {:d}\r\n'.format(
                self.remote_user.get_number())
            out += 'RS-232 Speed: {:d}\r\n'.format(
                self.remote_user.get_speed())
            out += '------------------------------------------\r\n'
            out += 'Enter C to enter phone connection\r\n'
            out += 'Enter D to disconnect from phone\r\n'
        else:
            phones = self._get_phones()
            out += 'You are not connected to any phones now!\r\n'
            out += 'Currently {:d} phones connected to server\r\n'.format(
                len(phones))
            if phones:
                for phone in phones:
                    status = 'free'
                    if phone.remote_user:
                        status = 'occupied'
                    out += '[{}] {} {}\r\n'.format(phone.get_number(),
                                                   phone.get_addr(), status)
                out += '--------------------------------------------------------\r\n'
                out += ' - D [number] - Force disconnect phone\r\n'
                out += ' - C [number] {speed_num} - Connect to phone with speed:\r\n'
                for ind in range(0, len(self._SPEED_MODES)):
                    if ind == self._DEFAULT_SPEED:
                        out += '\t{:d} - {:d} default\r\n'.format(
                            ind, self._SPEED_MODES[ind])
                    else:
                        out += '\t{:d} - {:d}\r\n'.format(
                            ind, self._SPEED_MODES[ind])
                out += '--------------------------------------------------------\r\n'

        out += '\r\nEnter command: '

        self._sends(out)

    def _disconnect(self):
        self.remote_user.remote_user = None
        self.remote_user = None

    def _connect(self, phones, number, speed=None):
        phone_finded = None
        for phone in phones:
            if number == phone.get_number():
                phone_finded = phone
                break
        if not phone_finded:
            self._sends("no phone with number {:d}".format(number))
            return

        if speed is None:
            speed = self._DEFAULT_SPEED

        phone_finded.set_speed(self._SPEED_MODES[speed])
        phone_finded.remote_user = self
        self.remote_user = phone_finded
        self._enter_connect_mode()

    def _force_disconnect(self, phones, number):
        phone_finded = None
        for phone in phones:
            if number == phone.get_number():
                phone_finded = phone
                break
        if not phone_finded:
            self._sends("no phone with number {:d}".format(number))
            return
        phone_finded.force_close()
        self._sends("Disconnected {:d}!".format(number))

    def force_close(self):
        """force close"""
        if self.remote_user:
            self.remote_user.remote_user = None
            self.remote_user = None
        del self._user_list[self._sock]
        self._sock.close()

    def _menu_anal(self, data):
        #catch ^C
        if data == b'\xfd\x06':
            self.force_close()
            return

        cmds = data.decode(
            'utf-8', errors='ignore').replace('\r', '').replace(
                '\n', '').upper().split(' ')

        if self.remote_user:
            #connected
            if len(cmds) == 1:
                if cmds[0] == 'C':
                    self._enter_connect_mode()
                    return
                if cmds[0] == 'D':
                    self._disconnect()
        else:
            #disconnected
            phones = self._get_phones()
            if phones and len(cmds) > 1:
                if cmds[0] == 'C':
                    #connect
                    if len(cmds) == 3:
                        self._connect(phones, int(cmds[1]), int(cmds[2]))
                    else:
                        self._connect(phones, int(cmds[1]))
                    return
                if cmds[0] == 'D':
                    self._force_disconnect(phones, int(cmds[1]))
                    return

        self._menu_out()

    def _connect_anal(self, data):
        for bte in data:
            if bte == 0x1b:  #ctrl + [
                self._enter_menu_mode()
                return
        if self.remote_user:
            self.remote_user.send(data)
        else:
            self._sends("no remote user -> switch to menu\r\n")
            self._enter_menu_mode()

    def handle_data(self, data):
        """This method handle data"""
        data = iac_filter(data)
        if data:
            if self._menu_mode:
                self._menu_anal(data)
            else:
                self._connect_anal(data)

    def _sends(self, datastr):
        """This method send string"""
        self._send(datastr.encode('utf-8'))

    def _send(self, data):
        """This method send bytes"""
        self._sock.send(data)

    def send(self, data):
        """This public method send bytes from phones"""
        if self._menu_mode:
            return

        if not self.remote_user:
            return

        self._send(iac_protect(data))

    def close(self):
        """close all resources"""
        if self.remote_user:
            self.remote_user.remote_user = None
