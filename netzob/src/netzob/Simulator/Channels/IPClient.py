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
#|       - Frédéric Guihéry <frederic.guihery (a) amossys.fr>                |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Standard library imports                                                  |
#+---------------------------------------------------------------------------+
import socket

#+---------------------------------------------------------------------------+
#| Related third party imports                                               |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Local application imports                                                 |
#+---------------------------------------------------------------------------+
from netzob.Common.Utils.Decorators import typeCheck, NetzobLogger
from netzob.Simulator.Channels.AbstractChannel import AbstractChannel


@NetzobLogger
class IPClient(AbstractChannel):
    """An IPClient is a communication channel to send IP
    payloads. The **kernel** is responsible to build the IP header. It is
    similar to RawIPClient channel, except that with RawIPClient the
    channel builds the IP header. Therefore, with :class:`IPClient <netzob.Simulator.Channels.IPClient.IPClient>`,
    we **cannot** modify or fuzz the IP header fields.

    The IPClient constructor expects some parameters:

    :param remoteIP: The remote IP address to connect to.
    :param localIP: The local IP address. Default value is the local
                    IP address corresponding to the interface that
                    will be used to send the packet.
    :param upperProtocol: The protocol following the IP header.
                          Default value is socket.IPPROTO_TCP.
    :param interface: The network interface to use. It is linked with
                      the local IP address to use (`localIP` parameter).
                      Default value is 'eth0'.
    :param timeout: The default timeout of the channel for opening
                    connection and waiting for a message. Default value
                    is 5.0 seconds. To specify no timeout, None value is
                    expected.
    :type remoteIP: :class:`str`, required
    :type localIP: :class:`str`, optional
    :type upperProtocol: :class:`int`, optional
    :type interface: :class:`str`, optional
    :type timeout: :class:`float`, optional


    The following code shows the use of an IPClient channel:

    >>> from netzob.all import *
    >>> client = IPClient(remoteIP='127.0.0.1')
    >>> client.open()
    >>> symbol = Symbol([Field("Hello everyone!")])
    >>> client.write(symbol.specialize())
    >>> client.close()

    """

    @typeCheck(str, int)
    def __init__(self,
                 remoteIP,
                 localIP=None,
                 upperProtocol=socket.IPPROTO_TCP,
                 interface="eth0",
                 timeout=5.):
        super(IPClient, self).__init__(isServer=False)
        self.remoteIP = remoteIP
        self.localIP = localIP
        self.upperProtocol = upperProtocol
        self.interface = interface
        self.timeout = timeout
        self.type = AbstractChannel.TYPE_IPCLIENT
        self.__socket = None

    def open(self):
        """Open the communication channel. If the channel is a client, it
        starts to connect to the specified server.
        """

        if self.isOpen:
            raise RuntimeError(
                "The channel is already open, cannot open it again")

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, self.upperProtocol)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**30)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**30)
        self.__socket.bind((self.localIP, self.upperProtocol))
        self.isOpen = True

    def close(self):
        """Close the communication channel."""
        if self.__socket is not None:
            self.__socket.close()
        self.isOpen = False

    def read(self):
        """Read the next message on the communication channel.
        """
        if self.__socket is not None:
            (data, _) = self.__socket.recvfrom(65535)

            return data
        else:
            raise Exception("socket is not available")

    def writePacket(self, data):
        """Write on the communication channel the specified data

        :param data: the data to write on the channel
        :type data: :class:`bytes`
        """
        if self.__socket is not None:
            len_data = self.__socket.sendto(data, (self.remoteIP, 0))
            return len_data
        else:
            raise Exception("socket is not available")

    def sendReceive(self, data):
        """Write on the communication channel the specified data and returns
        the corresponding response.

        :param data: the data to write on the channel
        :type data: :class:`bytes`

        """
        if self.__socket is not None:
            # get the ports from message to identify the good response
            #  (in TCP or UDP)

            portSrcTx = (data[0] * 256) + data[1]
            portDstTx = (data[2] * 256) + data[3]

            responseOk = False
            stopWaitingResponse = False
            self.write(data)
            while stopWaitingResponse is False:
                dataReceived = self.read()

                # IHL = (Bitwise AND 00001111) x 4bytes
                ipHeaderLen = (dataReceived[0] & 15) * 4
                portSrcRx = (dataReceived[ipHeaderLen] * 256) + \
                    dataReceived[ipHeaderLen + 1]
                portDstRx = (dataReceived[ipHeaderLen + 2] * 256) + \
                    dataReceived[ipHeaderLen + 3]

                stopWaitingResponse = (portSrcTx == portDstRx) and \
                    (portDstTx == portSrcRx)
                if stopWaitingResponse:  # and not timeout
                    responseOk = True
            if responseOk:
                return dataReceived
        else:
            raise Exception("socket is not available")

    # Management methods

    # Properties

    @property
    def remoteIP(self):
        """IP on which the server will listen.

        :type: :class:`str`
        """
        return self.__remoteIP

    @remoteIP.setter
    @typeCheck(str)
    def remoteIP(self, remoteIP):
        if remoteIP is None:
            raise TypeError("Listening IP cannot be None")

        self.__remoteIP = remoteIP

    @property
    def localIP(self):
        """IP on which the server will listen.

        :type: :class:`str`
        """
        return self.__localIP

    @localIP.setter
    @typeCheck(str)
    def localIP(self, localIP):
        self.__localIP = localIP

    @property
    def upperProtocol(self):
        """Upper protocol, such as TCP, UDP, ICMP, etc.

        :type: :class:`str`
        """
        return self.__upperProtocol

    @upperProtocol.setter
    @typeCheck(int)
    def upperProtocol(self, upperProtocol):
        if upperProtocol is None:
            raise TypeError("Upper protocol cannot be None")

        self.__upperProtocol = upperProtocol

    @property
    def interface(self):
        """Interface such as eth0, lo.

        :type: :class:`str`
        """
        return self.__interface

    @interface.setter
    @typeCheck(str)
    def interface(self, interface):
        if interface is None:
            raise TypeError("Interface cannot be None")

        self.__interface = interface

    @property
    def timeout(self):
        """The default timeout of the channel for opening connection and
        waiting for a message. Default value is 5.0 seconds. To
        specify no timeout, None value is expected.

        :rtype: :class:`float` or None
        """
        return self.__timeout

    @timeout.setter
    @typeCheck(float)
    def timeout(self, timeout):
        """
        :type timeout: :class:`float`, optional
        """
        self.__timeout = timeout
