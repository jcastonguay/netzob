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

#+---------------------------------------------------------------------------+
#| Related third party imports                                               |
#+---------------------------------------------------------------------------+
from PyCRC.CRC16 import CRC16 as _CRC16

#+---------------------------------------------------------------------------+
#| Local application imports                                                 |
#+---------------------------------------------------------------------------+
from netzob.Model.Vocabulary.Domain.Variables.Leafs.Checksum import Checksum
from netzob.Model.Vocabulary.Types.AbstractType import UnitSize


class CRC16(Checksum):
    r"""This class implements the CRC16 function.

    The constructor expects some parameters:

    :param targets: The targeted fields of the relationship.
    :param dataType: Specify that the produced value should be
                     represented according to this dataType.
                     If None, default value is Raw(nbBytes=2).
    :type targets: a :class:`list` of :class:`AbstractField <netzob.Model.Vocabulary.AbstractField>`, required
    :type dataType: :class:`AbstractType <netzob.Model.Vocabulary.Types.AbstractType>`, optional


    The following example shows how to create a checksum relation with
    another field:

    >>> from netzob.all import *
    >>> import binascii
    >>> f1 = Field(Raw(b'\xaa\xbb'))
    >>> f2 = Field(CRC16([f1]))
    >>> s = Symbol(fields = [f1, f2])
    >>> binascii.hexlify(s.specialize())
    b'aabb3ed3'
    """

    def calculate(self, msg):
        return _CRC16().calculate(msg)

    def getBitSize(self):
        return UnitSize.SIZE_16.value
