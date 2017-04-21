# -*- coding: utf-8 -*-

# +---------------------------------------------------------------------------+
# |          01001110 01100101 01110100 01111010 01101111 01100010            |
# |                                                                           |
# |               Netzob : Inferring communication protocols                  |
# +---------------------------------------------------------------------------+
# | Copyright (C) 2011-2017 Georges Bossert and Frédéric Guihéry              |
# | This program is free software: you can redistribute it and/or modify      |
# | it under the terms of the GNU General Public License as published by      |
# | the Free Software Foundation, either version 3 of the License, or         |
# | (at your option) any later version.                                       |
# |                                                                           |
# | This program is distributed in the hope that it will be useful,           |
# | but WITHOUT ANY WARRANTY; without even the implied warranty of            |
# | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              |
# | GNU General Public License for more details.                              |
# |                                                                           |
# | You should have received a copy of the GNU General Public License         |
# | along with this program. If not, see <http://www.gnu.org/licenses/>.      |
# +---------------------------------------------------------------------------+
# | @url      : http://www.netzob.org                                         |
# | @contact  : contact@netzob.org                                            |
# | @sponsors : Amossys, http://www.amossys.fr                                |
# |             Supélec, http://www.rennes.supelec.fr/ren/rd/cidre/           |
# |             ANSSI,   https://www.ssi.gouv.fr                              |
# +---------------------------------------------------------------------------+

# +---------------------------------------------------------------------------+
# | File contributors :                                                       |
# |       - Georges Bossert <georges.bossert (a) supelec.fr>                  |
# |       - Frédéric Guihéry <frederic.guihery (a) amossys.fr>                |
# +---------------------------------------------------------------------------+

# +---------------------------------------------------------------------------+
# | Standard library imports                                                  |
# +---------------------------------------------------------------------------+

# +---------------------------------------------------------------------------+
# | Related third party imports                                               |
# +---------------------------------------------------------------------------+
from bitarray import bitarray

# +---------------------------------------------------------------------------+
# | Local application imports                                                 |
# +---------------------------------------------------------------------------+
from netzob.Common.Utils.Decorators import NetzobLogger
from netzob.Common.Utils.Decorators import typeCheck
from netzob.Model.Vocabulary.AbstractField import AbstractField
from netzob.Common.Utils.TypedList import TypedList
from netzob.Model.Vocabulary.Messages.AbstractMessage import AbstractMessage
from netzob.Model.Vocabulary.Field import Field
from netzob.Model.Vocabulary.Domain.Variables.Memory import Memory
from netzob.Model.Vocabulary.Types.Raw import Raw
from netzob.Model.Vocabulary.Types.BitArray import BitArray
from netzob.Model.Vocabulary.Types.TypeConverter import TypeConverter


class Symbol(AbstractField):
    """The Symbol class is a main component of the Netzob protocol model.

    A symbol represents an abstraction of all messages of the same
    type from a protocol perspective. A symbol structure is made of
    fields.

    The Symbol constructor expects some parameters:

    :param fields: The fields that participate in the symbol
                   definition.  May be None, especially when using
                   Symbols for reverse engineering (i.e. fields
                   identification).
    :param messages: The messages that are associated with the
                     symbol. May be None, especially when
                     modeling a protocol from scratch (i.e. the
                     fields are already known).
    :param str name: The name of the symbol. If not specified, the
                     default name will be "Symbol".
    :type fields: a :class:`list` of :class:`Field <netzob.Model.Vocabulary.Field>`
    :type messages: a :class:`list` of :class:`AbstractMessage <netzob.Model.Vocabulary.Messages.AbstractMessage>`


    **Usage of Symbol for protocol modeling**

    The Symbol class may be used to model a protocol from scratch, by
    specifying its structure in terms of fields:

    >>> f0 = Field("aaaa")
    >>> f1 = Field(" # ")
    >>> f2 = Field("bbbbbb")
    >>> symbol = Symbol(fields=[f0, f1, f2])
    >>> print(symbol._str_debug())
    Symbol
    |--  Field
         |--   Data (ASCII=aaaa ((0, 32)))
    |--  Field
         |--   Data (ASCII= #  ((0, 24)))
    |--  Field
         |--   Data (ASCII=bbbbbb ((0, 48)))

    **Usage of Symbol for protocol dissecting**

    The Symbol class may be used to dissect a list of messages
    according to the fields structure:

    >>> from netzob.all import *
    >>> f0 = Field("hello", name="f0")
    >>> f1 = Field(ASCII(nbChars=(0, 10)), name="f1")
    >>> m1 = RawMessage("hello world")
    >>> m2 = RawMessage("hello earth")
    >>> symbol = Symbol(fields=[f0, f1], messages=[m1, m2])
    >>> print(symbol)
    f0      | f1      
    ------- | --------
    'hello' | ' world'
    'hello' | ' earth'
    ------- | --------

    **Usage of Symbol for protocol reverse engineering**

    The Symbol class may be used is to do reverse engineering on a
    list of captured messages of unknown/undocumented protocols:

    >>> from netzob.all import *
    >>> m1 = RawMessage("hello aaaa")
    >>> m2 = RawMessage("hello bbbb")
    >>> symbol = Symbol(messages=[m1, m2])
    >>> Format.splitStatic(symbol)
    >>> print(symbol)
    Field-0  | Field-1
    -------- | -------
    'hello ' | 'aaaa' 
    'hello ' | 'bbbb' 
    -------- | -------

    **Usage of Symbol for traffic generation**

    A Symbol class may be used to generate concrete messages according
    to its fields definition, through the `specialize()` method, and
    may also be used to abstract a concrete message into its
    associated symbol through the `abstract()` method:

    >>> f0 = Field("aaaa")
    >>> f1 = Field(" # ")
    >>> f2 = Field("bbbbbb")
    >>> symbol = Symbol(fields=[f0, f1, f2])
    >>> concrete_message = symbol.specialize()
    >>> print(concrete_message)
    b'aaaa # bbbbbb'
    >>> (abstracted_symbol, structured_data) = AbstractField.abstract(concrete_message, [symbol])
    >>> print(abstracted_symbol == symbol)
    True

    """

    def __init__(self, fields=None, messages=None, name="Symbol"):
        super(Symbol, self).__init__(name)
        self.__messages = TypedList(AbstractMessage)
        if messages is None:
            messages = []
        self.messages = messages
        if fields is None:
            # create a default empty field
            fields = [Field()]
        self.fields = fields

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        if other is None:
            return False
        return self.name == other.name

    def __ne__(self, other):
        if other is None:
            return True
        if not isinstance(other, Symbol):
            return True
        return other.name != self.name

    def __key(self):
        return self.id

    def __hash__(self):
        return hash(frozenset(self.name))

    @typeCheck(Memory, object)
    def specialize(self, memory=None, presets=None):
        """The method specialize() generates a :class:`bytes` sequence whose
        content follows the field or symbol definition.

        The specialize() method expects some parameters:

        :param memory: A memory used to store variables values during
                       specialization and abstraction of sequence of symbols.
        :param presets: A dictionary of keys:values used to preset
                        (parameterize) fields during symbol
                        specialization. Values in this dictionary will
                        override any fields definition, constraints or
                        relationship dependencies.
        :type memory: :class:`Memory <netzob.Model.Vocabulary.Domain.Variables.Memory>`
        :type presets: :class:`dict`

        The following example shows the specialize() method used for a
        field which contains an ASCII and a Size fields.

        >>> from netzob.all import *
        >>> f1 = Field(domain=ASCII(nbChars=5))
        >>> f0 = Field(domain=Size(f1))
        >>> s = Symbol(fields=[f0, f1])
        >>> result = s.specialize()
        >>> print(result[0])
        5
        >>> print(len(result))
        6

        **Presets of fields values**

        The following example shows the use of the presets parameter
        for some variables included in the symbol definition.

        >>> from netzob.all import *
        >>> f1 = Field(domain=ASCII("hello "))
        >>> f2 = Field(domain=ASCII(nbChars=(1,10)))
        >>> s = Symbol(fields = [f1, f2])
        >>> presetValues = dict()
        >>> presetValues[f2] = TypeConverter.convert("antoine", ASCII, BitArray)
        >>> print(s.specialize(presets = presetValues))
        b'hello antoine'

        A preseted valued bypasses all the constraints checks on your field definition.
        For example, in the following example it can be use to bypass a size field definition.

        >>> from netzob.all import *
        >>> f1 = Field()
        >>> f2 = Field(domain=Raw(nbBytes=(10,15)))
        >>> f1.domain = Size(f2)
        >>> s = Symbol(fields=[f1, f2])
        >>> presetValues = {f1: TypeConverter.convert("\xff", Raw, BitArray)}        
        >>> print(s.specialize(presets = presetValues)[0])
        195

        """

        from netzob.Model.Vocabulary.Domain.Specializer.MessageSpecializer import MessageSpecializer
        msg = MessageSpecializer(memory=memory, presets=presets)
        spePath = msg.specializeSymbol(self)

        if spePath is not None:
            return TypeConverter.convert(spePath.generatedContent, BitArray,
                                         Raw)

    def clearMessages(self):
        """Delete all the messages attached to the current symbol"""
        while (len(self.__messages) > 0):
            self.__messages.pop()

    # Properties

    @property
    def messages(self):
        """A list containing all the messages that this symbol represent.

        :type : a :class:`list` of :class:`AbstractMessage <netzob.Model.Vocabulary.Messages.AbstractMessage.AbstractMessage>`
        """
        return self.__messages

    @messages.setter
    def messages(self, messages):
        if messages is None:
            messages = []

        # First it checks the specified messages are all AbstractMessages
        for msg in messages:
            if not isinstance(msg, AbstractMessage):
                raise TypeError(
                    "Cannot add messages of type {0} in the session, only AbstractMessages are allowed.".
                    format(type(msg)))

        self.clearMessages()
        for msg in messages:
            self.__messages.append(msg)

    def __repr__(self):
        return self.name
