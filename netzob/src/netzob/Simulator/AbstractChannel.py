#-*- coding: utf-8 -*-

#+---------------------------------------------------------------------------+
#|          01001110 01100101 01110100 01111010 01101111 01100010            |
#|                                                                           |
#|               Netzob : Inferring communication protocols                  |
#+---------------------------------------------------------------------------+
#| Copyright (C) 2011-2017 Georges Bossert and Frédéric Guihéry              |
#| This program is free software: you can redistribute it and/or modify      |
#| it under the terms of the GNU General Public License as published by      |
#| the Free Software Foundation, either version 3 of the License, or         |
#| (at your option) any later version.                                       |
#|                                                                           |
#| This program is distributed in the hope that it will be useful,           |
#| but WITHOUT ANY WARRANTY; without even the implied warranty of            |
#| MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              |
#| GNU General Public License for more details.                              |
#|                                                                           |
#| You should have received a copy of the GNU General Public License         |
#| along with this program. If not, see <http://www.gnu.org/licenses/>.      |
#+---------------------------------------------------------------------------+
#| @url      : http://www.netzob.org                                         |
#| @contact  : contact@netzob.org                                            |
#| @sponsors : Amossys, http://www.amossys.fr                                |
#|             Supélec, http://www.rennes.supelec.fr/ren/rd/cidre/           |
#|             ANSSI,   https://www.ssi.gouv.fr                              |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| File contributors :                                                       |
#|       - Georges Bossert <georges.bossert (a) supelec.fr>                  |
#|       - Frédéric Guihéry <frederic.guihery (a) amossys.fr>                |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Standard library imports                                                  |
#+---------------------------------------------------------------------------+
import abc
import array
import binascii
import socket
import struct
import subprocess
import sys
import time
from fcntl import ioctl
from itertools import repeat
from typing import Any, Callable, List, Type  # noqa: F401
from threading import Thread, Event
#from multiprocessing import Process, Event
from queue import Queue, Empty
#from multiprocessing import Queue


#+---------------------------------------------------------------------------+
#| Related third party imports                                               |
#+---------------------------------------------------------------------------+
import arpreq

#+---------------------------------------------------------------------------+
#| Local application imports                                                 |
#+---------------------------------------------------------------------------+
from netzob.Common.Utils.Decorators import typeCheck, public_api, NetzobLogger
from netzob.Simulator.ChannelBuilder import ChannelBuilder  # noqa: F401


class ChannelDownException(Exception):
    pass


@NetzobLogger
class ChannelInterface(object, metaclass=abc.ABCMeta):
    """The ChannelInterface class specifies the methods to implement in
    order to create a new communication channel.

    The following methods have to be implemented:

    * :meth:`~.open`
    * :meth:`~.close`
    * :meth:`~.read`
    * :meth:`~.writePacket`
    * :meth:`~.sendReceive`

    To associate a channel into a group a *similar* channels, class should
    declare a list of compatible families. An empty list of families means that
    the channel is *similar* to all possible families.

    """

    # Class attributes ##

    FAMILIES = []  # type: List[str]
    """
    **Class attribute**.

    :class:`~typing.List` of families.
    This attribute should be superseded in child classes.
    An empty list means that the channel is *similar* to all possible families.

    :type: :class:`List[str]`
    """

    # Class internal attributes #

    DEFAULT_WRITE_COUNTER_MAX = -1
    DEFAULT_TIMEOUT = None

    # Interface methods ##

    @public_api
    def __init__(self):
        pass

    @public_api
    @abc.abstractmethod
    def open(self, timeout=DEFAULT_TIMEOUT):
        """Open the communication channel. If the channel is a server, it
        starts to listen for incoming data. If the channel is a client, it connects to the remote peer.

        :param timeout: The timeout of the channel for opening
                        a connection with a remote peer. This parameter overrides the channel :attr:`timeout` attribute and is only effective in the context of a client. Default value (None) corresponds to no timeout.
        :type timeout: :class:`float`, optional

        """
        if self.isOpen:
            raise RuntimeError(
                "The channel is already open, cannot open it again")

    @public_api
    @abc.abstractmethod
    def close(self):
        """Close the communication channel."""

    @public_api
    @abc.abstractmethod
    def read(self):
        """Read the next message from the communication channel.

        :return: The received data.
        :rtype: :class:`bytes`

        """

    @public_api
    @abc.abstractmethod
    def writePacket(self, data):
        """Write on the communication channel the specified data.

        :param data: The data to write on the channel.
        :type data: :class:`bytes`
        """

    @public_api
    @abc.abstractmethod
    def sendReceive(self, data):
        """Write on the communication channel the specified data, wait for a
        response and return the received data.

        :param data: The data to write on the channel.
        :type data: :class:`bytes`, required
        :return: The received data.
        :rtype: :class:`bytes`

        """


@public_api
@NetzobLogger
class AbstractChannel(ChannelInterface, Thread, metaclass=abc.ABCMeta):
    """A communication channel is an element allowing the establishment of a
    connection to or from a remote device.

    The AbstractChannel defines the API of a communication channel.

    A communication channel provides the following public variables:

    :var isOpen: The status of the communication channel.
    :var timeout: The default timeout in seconds for opening a connection (only effective in the context of a client), as well as for
                  waiting a message when calling the :meth:`read` method.
    :var header: A Symbol that makes it possible to access the protocol header.
    :var header_preset: A Preset used to preset
                        (parameterize) the header fields during symbol
                        specialization. See :meth:`Symbol.specialize() <netzob.Model.Vocabulary.Symbol.Symbol.specialize>` for more information.
    :vartype isOpen: :class:`bool`
    :vartype timeout: :class:`int`
    :vartype header: :class:`~netzob.Model.Vocabulary.Symbol.Symbol`
    :vartype header_preset: :class:`~netzob.Model.Vocabulary.Preset`

    """

    # Abstract methods ##

    @abc.abstractstaticmethod
    def getBuilder():
        # type: () -> Type[ChannelBuilder]
        """
        Provide the builder specific to an :class:`AbstractChannel`
        """

    # Public API methods ##

    def register_abstraction_layer(self, abstraction_layer):
        self.registered_abstraction_layers.append(abstraction_layer)

    def unregister_abstraction_layer(self, abstraction_layer):
        if abstraction_layer in self.registered_abstraction_layers:
            self.registered_abstraction_layers.remove(abstraction_layer)

    @public_api
    def setSendLimit(self, maxValue):
        """Change the max number of writings.

        When it is reached, no more packets can be sent until
        :meth:`clearSendLimit` is called.

        If maxValue is -1, the sending limit is deactivated.

        :param maxValue: the new max value
        :type maxValue: :class:`int`, required
        """
        self.__writeCounterMax = maxValue

    @public_api
    def clearSendLimit(self):
        """Reset the writing counters.
        """
        self.__writeCounter = 0
        self.__writeCounterMax = AbstractChannel.DEFAULT_WRITE_COUNTER_MAX

    @public_api
    def write(self, data, rate=None, duration=None):
        """Write to the communication channel the specified data, either once,
        or in a loop according to the `rate` and `duration`
        parameters.

        :param data: The data to write on the channel.
        :param rate: This specifies the bandwidth in octets to respect during
                     traffic emission (should be used with :attr:`duration` parameter).
        :param duration: This indicates for how many seconds the data is continuously
                         written on the channel.
        :type data: bytes, required
        :type rate: int, optional
        :type duration: int, optional
        :return: The amount of written data, in bytes.
        :rtype: int

        """

        if self.threaded_mode:
            self.queue_output.put(data)
            return len(data)
        else:
            return self.write_map(repeat(data), rate=rate, duration=duration)

    @public_api
    def write_map(self, data_iterator, rate=None, duration=None):
        """Write to the communication channel the successive data values,
        either once, or in a loop according to the `rate` and `duration`
        parameters.

        :param data_iterator: data iterator used to write on the channel.
        :param rate: This specifies the bandwidth in octets to respect during
                     traffic emission (should be used with duration= parameter).
        :param duration: This indicates for how many seconds the data is continuously
                         written on the channel.
        :type data_iterator: ~typing.Iterator[bytes], required
        :type rate: int, optional
        :type duration: int, optional
        :return: The amount of written data, count in bytes.
        :rtype: int

        """
        if ((self.__writeCounterMax > 0) and
           (self.__writeCounter > self.__writeCounterMax)):
            raise Exception("Max write counter reached ({})"
                            .format(self.__writeCounterMax))

        self.__writeCounter += 1
        len_data = 0
        if duration is None:
            try:
                data = next(data_iterator)
            except StopIteration:
                len_data = 0
            else:
                len_data = self.writePacket(data)
        else:
            rate_text = "unlimited"
            rate_unlimited = True
            if type(rate) is int and rate > 0:
                rate_text = "{:.2f} kBps".format(rate / 1024)
                rate_unlimited = False

            t_start = time.time()
            t_elapsed = 0
            t_delta = 0
            for data in data_iterator:

                t_elapsed = time.time() - t_start
                if t_elapsed > duration:
                    break

                # Specialize the symbol and send it over the channel
                len_data += self.writePacket(data)

                while True:
                    t_tmp = t_elapsed
                    t_elapsed = time.time() - t_start
                    t_delta += t_elapsed - t_tmp

                    if not rate_unlimited and (len_data / t_elapsed) > rate:
                        time.sleep(0.001)
                    else:
                        break

                # Show some log every seconds
                if t_delta > 1:
                    t_delta = 0
                    self._logger.debug("Rate rule: {}, current rate: {:.2f} kBps, "
                                       "sent data: {:.2f} kB, nb seconds elapsed: "
                                       "{:.2f}".format(rate_text,
                                                       len_data / t_elapsed / 1024,
                                                       len_data / 1024,
                                                       t_elapsed, 2))
        return len_data

    @public_api
    def checkReceived(self,
                      predicate,  # type: Callable[..., bool]
                      *args, **kwargs):
        # type: (...) -> bool
        """
        Method used to delegate the validation of the received data into
        a callback

        :param predicate: the function used to validate the received data
        :param args: positional arguments passed to ``predicate``
        :param kwargs: named arguments passed to ``predicate``
        :type predicate: ~typing.Callable[[bytes], bool], required
        """
        if not callable(predicate):
            raise ValueError("The predicate attribute must be a callable "
                             "expecting a single bytes attribute, not '{}'"
                             .format(type(predicate).__name__))
        return predicate(self.read(), *args, **kwargs)


    @public_api
    def __init__(self, timeout=ChannelInterface.DEFAULT_TIMEOUT):
        """
        :param timeout: The default timeout of the channel for global
                        connection. Default value is blocking (None).
        :type timeout: :class:`float`, optional

        """

        Thread.__init__(self)
        ChannelInterface.__init__(self)
        self._socket = None
        self.timeout = timeout
        self._isOpened = False
        self.header = None  # A Symbol corresponding to the protocol header
        self.header_preset = None  # A Preset object is expected to parameterize the header Symbol
        self.__writeCounter = 0
        self.__writeCounterMax = AbstractChannel.DEFAULT_WRITE_COUNTER_MAX

        self.registered_abstraction_layers = []

        # Threading management
        self.threaded_mode = False
        self.__stopEvent = Event()
        self.__queue_output = Queue()


    ## Internal methods ##

    @public_api
    def __enter__(self):
        """Enter the runtime channel context by opening the channel.
        This methods is implied in the with statement.
        """
        self.open()
        return self

    @public_api
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime channel context by closing the channel.
        This methods is implied in the with statement.
        """
        self.close()

    def updateSocketTimeout(self):
        """Update the timeout of the socket."""
        if self._socket is not None:
            self._socket.settimeout(self.timeout)


    ## Thread management ##

    def run(self):
        self._logger.debug("Starting channel thread")
        self.threaded_mode = True

        self.timeout = 0.1

        self.open()

        while not self.__stopEvent.is_set():
            self.process_data_to_send()

            data = self.check_incoming_data()

            if data is not None and len(data) > 0:
                self.process_incoming_data(data)
        self._logger.debug("Exiting channel thread")

    def process_data_to_send(self):
        while not self.queue_output.empty():  # Test if the queue is not empty
            self._logger.debug("Process data to send")
            try:
                data = self.queue_output.get()
            except Empty:
                self._logger.warning("Queue error")
                raise
            try:
                self.writePacket(data)
            except PermissionError as e:
                self._logger.warning("Error on socket writing: '{}'".format(e))
            self.queue_output.task_done()
            self._logger.debug("Data sent")

    def check_incoming_data(self):
        try:
            data = self.read()
            self._logger.debug("Received : {}".format(repr(data)))
        except socket.timeout:
            data = None
        except Exception as e:
            if not self.isActive():
                return
            else:
                self._logger.debug("Exception on read(): '{}'".format(e))
            raise
        else:
            return data

    def process_incoming_data(self, data):
        #self._logger.debug("Processing read data")

        for abstraction_layer in self.registered_abstraction_layers:
            if abstraction_layer.is_data_interesting(data):
                self._logger.debug("Adding received message to input queue of abstraction layer '{}'".format(id(abstraction_layer)))
                abstraction_layer.queue_input.put(data)

    @public_api
    def stop(self):
        """Stop the current thread.

        This operation is not immediate because we try to stop the
        thread as cleanly as possible.

        """

        # Stop channel
        self._logger.debug("Stopping the current channel")
        self.close()

        self.__stopEvent.set()

    @public_api
    def wait(self):
        """Wait for the current thread to finish processing.

        """
        while self.isActive():
            time.sleep(0.5)

    @public_api
    def isActive(self):
        """Indicate if the current thread is active.

        :return: True if the thread execution has not finished.
        :rtype: :class:`bool`
        """
        return not self.__stopEvent.is_set()

    @public_api
    def flush(self):
        """Block until the channel output queue is empty.

        """
        self.queue_output.join()

    ## Properties ##

    @property
    def isOpen(self):
        """
        Property (getter.setter  # type: ignore).
        Returns ``True`` if the communication channel is open.

        :return: The status of the communication channel.
        :type: :class:`bool`
        """
        return self._isOpened

    @isOpen.setter  # type: ignore
    @typeCheck(bool)
    def isOpen(self, isOpen):
        self._isOpened = isOpen

    @property
    def queue_output(self):
        return self.__queue_output

    @queue_output.setter  # type: ignore
    def queue_output(self, queue_output):
        self.__queue_output = queue_output

    @property
    def timeout(self):
        """The default timeout of the channel for opening connection and
        waiting for a message. Default value is DEFAULT_TIMEOUT seconds
        (float). To specify no timeout, None value is expected.

        :rtype: :class:`float` or None
        """
        return self._timeout

    @timeout.setter  # type: ignore
    @typeCheck((int, float, type(None)))
    def timeout(self, timeout):
        """
        :type timeout: :class:`float`, optional
        """
        self._timeout = None if timeout is None else float(timeout)
        self.updateSocketTimeout()


# Utilitary methods ##

class NetUtils(object):
    """A utilitary class that provides static methods to handle network
    address and interface resolutions.

    """

    @staticmethod
    def getRemoteMacAddress(remoteIP):
        """
        Retrieve remote MAC address from the remote IP address
        """
        dstMacAddr = arpreq.arpreq(remoteIP)
        if dstMacAddr is not None:
            dstMacAddr = dstMacAddr.replace(':', '')
            dstMacAddr = binascii.unhexlify(dstMacAddr)
        else:
            # Force ARP resolution
            p = subprocess.Popen(["/bin/ping", "-c1", remoteIP])
            p.wait()
            time.sleep(0.1)

            dstMacAddr = arpreq.arpreq(remoteIP)
            if dstMacAddr is not None:
                dstMacAddr = dstMacAddr.replace(':', '')
                dstMacAddr = binascii.unhexlify(dstMacAddr)
            else:
                raise Exception("Cannot resolve IP address to a MAC address for IP: '{}'".format(remoteIP))
        return dstMacAddr

    @staticmethod
    def getLocalMacAddress(interface):
        """
        Retrieve local MAC address from the network interface.
        """
        def get_interface_addr(ifname):
            s = socket.socket()
            response = ioctl(s,
                             0x8927,  # SIOCGIFADDR
                             struct.pack("16s16x", ifname))
            s.close()
            return struct.unpack("16xh6s8x", response)

        srcMacAddr = get_interface_addr(bytes(interface, 'utf-8'))[1]
        return srcMacAddr

    # Static methods used to retrieve local network interface
    # and local IP according to a remote IP

    @staticmethod
    def getIPFromInterface(ifname):
        """
        Retrieve the local IP corresponding to the given local network
        interface.

        :param ifname: The network interface name.
        :type ifname: :class:`str`
        :return: The local IP address.
        :type: :class:`str`
        """

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])

    @staticmethod
    def getLocalInterface(localIP):
        """
        Retrieve the network interface from the local IP address.

        :param localIP: The local IP address
        :type localIP: :class:`str`
        :return: The network interface name.
        :type: :class:`str`
        """

        for (networkInterface, ip) in NetUtils.getLocalInterfaces():
            if localIP == ip:
                return networkInterface
        return None

    @staticmethod
    def getLocalIP(remoteIP):
        """Retrieve the source IP address which will be used to connect to the
        destination IP address.

        :param remoteIP: the remote IP address
        :type localIP: :class:`str`
        """

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((remoteIP, 53))
        localIPAddress = s.getsockname()[0]
        s.close()
        return localIPAddress

    @staticmethod
    def getLocalInterfaces():
        """ Retrieve the list of all network interfaces and their associated IP.

        :return: The list of (interface name, IP) tuples.
        :type: :class:`list` of :class:`tuple` (:class:`str`, :class:`str`)
        """

        # source : http://code.activestate.com/recipes/439093-get-names-of-all-up-network-interfaces-linux-only/
        is_64bits = sys.maxsize > 2**32
        struct_size = 40 if is_64bits else 32
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        max_possible = 8  # initial value
        while True:
            _bytes = max_possible * struct_size
            names = array.array('B')
            for i in range(0, _bytes):
                names.append(0)
            outbytes = struct.unpack('iL', ioctl(
                s.fileno(),
                0x8912,  # SIOCGIFCONF
                struct.pack('iL', _bytes, names.buffer_info()[0])
            ))[0]
            if outbytes == _bytes:
                max_possible *= 2
            else:
                break
        namestr = names.tostring()
        ifaces = []
        for i in range(0, outbytes, struct_size):
            iface_name = bytes.decode(namestr[i:i+16]).split('\0', 1)[0]
            iface_addr = socket.inet_ntoa(namestr[i+20:i+24])
            ifaces.append((iface_name, iface_addr))

        return ifaces

    @staticmethod
    def getLocalInterfaceFromMac(localMac):
        """
        Retrieve the network interface from the local MAC address.

        :param localMac: The local MAC address
        :type localMac: :class:`str`
        :return: The network interface name.
        :type: :class:`str`
        """

        MacInBytes = localMac.replace(':', '')
        MacInBytes = binascii.unhexlify(MacInBytes)

        for (networkInterface, _) in NetUtils.getLocalInterfaces():
            if NetUtils.getLocalMacAddress(networkInterface) == MacInBytes:
                return networkInterface
        return None

    @staticmethod
    def getMtu(localInterface):
        """
        Retrieve the MTU of the given network interface.

        :param localInterface: The local network interface
        :type localInterface: :class:`str`
        :return: The MTU value.
        :type: :class:`int`
        """

        ifname = bytes(localInterface, 'utf-8')
        s = socket.socket(type=socket.SOCK_DGRAM)
        response = ioctl(s,
                         0x8921,  # SIOCGIFMTU
                         struct.pack("16s16x", ifname))
        mtu = struct.unpack("16xH14x", response)[0]
        return mtu

    @staticmethod
    def setMtu(localInterface, mtu):
        """
        Set the MTU of the given network interface.

        :param localInterface: The local network interface
        :type localInterface: :class:`str`
        """

        ifname = bytes(localInterface, 'utf-8')
        s = socket.socket(type=socket.SOCK_DGRAM)
        ioctl(s,
              0x8922,  # SIOCSIFMTU
              struct.pack("16sH14x", ifname, mtu))

    @staticmethod
    def isUp(localInterface):
        """
        Check if the given network interface is up.

        :param localInterface: The local network interface
        :type localInterface: :class:`str`
        """
        try:
            with open('/proc/mounts', 'r') as f:
                line = next(_ for _ in f.readlines() if 'sysfs' in _)
        except StopIteration:
            sysroot = '/sys'
        else:
            sysroot = line.split()[1]

        path = '{}/class/net/{}/operstate'.format(sysroot, localInterface)
        with open(path) as fd:
            return 'down' not in fd.read()
