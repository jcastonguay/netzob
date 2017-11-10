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
from netzob.Common.Utils.Decorators import typeCheck, NetzobLogger
from netzob.Model.Vocabulary.Domain.Variables.Leafs.AbstractVariableLeaf import AbstractVariableLeaf
from netzob.Model.Vocabulary.Domain.Specializer.SpecializingPath import SpecializingPath
from netzob.Model.Vocabulary.Domain.Parser.ParsingPath import ParsingPath
from netzob.Model.Vocabulary.Domain.GenericPath import GenericPath
from netzob.Model.Vocabulary.Types.AbstractType import AbstractType


@NetzobLogger
class Data(AbstractVariableLeaf):
    """The Data class is a variable which embeds specific content.

    A Data object stores at least two things: 1) the definition domain
    and the constraints over it, through a :class:`Type
    <netzob.Model.Vocabulary.Types.AbstractType>` object, and 2) the
    current value of the variable.

    The Data constructor expects some parameters:

    :param dataType: The type of the data (for example Integer,
                     Raw, String, ...).
    :param originalValue: The original value of the data (can be
                          None, which is the default behavior). The default value is None.
    :param name: The name of the data (if None, the name will
                 be generated).
    :param svas: The SVAS strategy defining how the Data value is
                 used during abstraction and specialization process.
                 The default strategy is SVAS.EPHEMERAL.
    :type dataType: :class:`AbstractType <netzob.Model.Vocabulary.Types.AbstractType.AbstractType>`, required
    :type originalValue: :class:`bitarray`, optional
    :type name: :class:`str`, optional
    :type svas: :class:`SVAS <netzob.Model.Vocabulary.Domain.Variables.SVAS.SVAS>`, optional


    The Data class provides the following public variables:

    :var currentValue: The current value of the data.
    :var dataType: The type of the data.
    :vartype currentValue: :class:`bitarray`
    :vartype dataType: :class:`AbstractType <netzob.Model.Vocabulary.Types.AbstractType>`


    The following example shows the definition of the Data `pseudo`
    with a type String and a default value `"hello"`. This means that
    this Data object accepts any string, and the current value
    of this object is `"hello"`.

    >>> from netzob.all import *
    >>> s = String('hello').value
    >>> data = Data(dataType=String(), originalValue=s, name="pseudo")
    >>> data.varType
    'Data'
    >>> data.currentValue.tobytes()
    b'hello'
    >>> print(data.dataType)
    String=None ((None, None))
    >>> data.name
    'pseudo'

    .. ifconfig:: scope in ('netzob')

       Besides, the Data object is the default Variable when we create a
       Field without explicitly specifying the Data domain, as shown in
       the following example:

       >>> from netzob.all import *
       >>> f = Field(String("hello"))
       >>> f.domain.varType
       'Data'
       >>> f.domain.currentValue.tobytes()
       b'hello'

    """

    def __init__(self, dataType, originalValue=None, name=None, svas=None):
        super(Data, self).__init__(
            self.__class__.__name__, name=name, svas=svas)

        self.dataType = dataType
        self.currentValue = originalValue

    def __str__(self):
        return "Data ({0})".format(self.dataType)

    def __key(self):
        return (self.__class__.__name__, self.currentValue, self.dataType,
                self.svas, self.name)

    @typeCheck(GenericPath)
    def isDefined(self, path):
        """Checks if a value is available either in data's definition or in memory

        :parameter path: the current path used either to abstract and specialize this data
        :type path: :class:`GenericPath <netzob.Model.Vocabulary.Domain.GenericPath.GenericPath>`
        :return: a boolean that indicates if a value is available for this data
        :rtype: :class:`bool`
        """

        if path is None:
            raise Exception("Path cannot be None")

        #  first we check if current value is assigned to the data
        if self.currentValue is not None:
            return True

        # we check if memory referenced its value (memory is priority)
        memory = path.memory

        if memory is None:
            raise Exception("Provided path has no memory attached.")

        return memory.hasValue(self)

    @typeCheck(ParsingPath)
    def domainCMP(self, parsingPath, acceptCallBack=True, carnivorous=False):
        """Checks if the value assigned to this variable could be parsed against
        the definition domain of the data.

        """

        if parsingPath is None:
            raise Exception("ParsingPath cannot be None")

        content = parsingPath.getData(self)

        self._logger.debug("DomainCMP {0} with {1}".format(content, self.dataType))

        (minSize, maxSize) = self.dataType.size
        if maxSize is None:
            maxSize = len(content)

        if len(content) < minSize:
            self._logger.debug(
                "Length of the content is too short ({0}), expect data of at least {1} bits".
                format(len(content), minSize))
        else:
            for size in range(min(maxSize, len(content)), minSize - 1, -1):
                # size == 0 : deals with 'optional' data
                if size == 0 or self.dataType.canParse(content[:size]):
                    # we create a new parsing path and returns it
                    newParsingPath = parsingPath.duplicate()

                    newParsingPath.addResult(self, content[:size].copy())
                    yield newParsingPath

    @typeCheck(ParsingPath)
    def valueCMP(self, parsingPath, acceptCallBack=True, carnivorous=False):
        if parsingPath is None:
            raise Exception("ParsingPath cannot be None")

        expectedValue = self.currentValue

        # we check a value is available in memory
        memory = parsingPath.memory
        if memory is None:
            raise Exception("No memory available")

        if memory.hasValue(self):
            expectedValue = memory.getValue(self)

        if expectedValue is None:
            raise Exception(
                "Data '{0}' has no value defined in its definition domain".
                format(self))

        content = parsingPath.getData(self)
        if content is None:
            raise Exception("No data assigned to the variable")

        results = []
        if len(content) >= len(expectedValue) and content[:len(
                expectedValue)].tobytes() == expectedValue.tobytes():
            parsingPath.addResult(self, content[:len(expectedValue)].copy())
            results.append(parsingPath)
            self._logger.debug("Data '{}' can be parsed with variable {}".format(content.tobytes(), self))
        else:
            self._logger.debug("Data '{}' cannot be parsed with variable {}".format(content.tobytes(), self))
        return results

    @typeCheck(ParsingPath)
    def learn(self, parsingPath, acceptCallBack=True, carnivorous=False):

        if parsingPath is None:
            raise Exception("ParsingPath cannot be None")

        content = parsingPath.getData(self)
        actualSize = len(content)

        self._logger.debug("Learn '{0}' with {1}".format(content.tobytes(),
                                                         self.dataType))

        try:
            minSize = maxSize = self.getFixedBitSize()
        except ValueError:
            (minSize, maxSize) = self.dataType.size
            if minSize is None:
                minSize = 0
            if maxSize is None:
                maxSize = actualSize

        if actualSize < minSize:
            self._logger.debug(
                "Length of the content is too short ({0}), expect data of at least {1} bits".
                format(len(content), minSize))
        else:
            for size in range(min(maxSize, len(content)), minSize - 1, -1):
                self._logger.debug("Try to parse {}/{} bits".format(size, maxSize))
                # size == 0 : deals with 'optional' data
                if size == 0 or self.dataType.canParse(content[:size]):
                    # we create a new parsing path and returns it
                    newParsingPath = parsingPath.duplicate()
                    addresult_succeed = newParsingPath.addResult(self, content[:size].copy())
                    if addresult_succeed:
                        newParsingPath.memory.memorize(self, content[:size].copy())
                        yield newParsingPath
                    else:
                        self._logger.debug("Parsed data does not respect a relation")

    @typeCheck(SpecializingPath)
    def use(self, variableSpecializerPath, acceptCallBack=True):
        """This method participates in the specialization proces.
        It creates a VariableSpecializerResult in the provided path that either
        contains the memorized value or the predefined value of the variable"""

        self._logger.debug("Use variable {0}".format(self))

        if variableSpecializerPath is None:
            raise Exception("VariableSpecializerPath cannot be None")

        memory = variableSpecializerPath.memory

        result = []

        if memory.hasValue(self):
            variableSpecializerPath.addResult(self, memory.getValue(self))
            result.append(variableSpecializerPath)
        elif self.currentValue is not None:
            variableSpecializerPath.addResult(self, self.currentValue)
            result.append(variableSpecializerPath)

        return result

    @typeCheck(SpecializingPath)
    def regenerate(self, variableSpecializerPath, acceptCallBack=True):
        """This method participates in the specialization proces.
        It creates a VariableSpecializerResult in the provided path that
        contains a generated value that follows the definition of the Data
        """
        self._logger.debug("Regenerate variable {0}".format(self))

        if variableSpecializerPath is None:
            raise Exception("VariableSpecializerPath cannot be None")

        newValue = self.dataType.generate()

        self._logger.debug("Generated value for {}: {}".format(self, newValue))

        variableSpecializerPath.addResult(self, newValue)
        return [variableSpecializerPath]

    @typeCheck(SpecializingPath)
    def regenerateAndMemorize(self,
                              variableSpecializerPath,
                              acceptCallBack=True):
        """This method participates in the specialization proces.
        It memorizes the value present in the path of the variable
        """

        self._logger.debug("Regenerate and memorize variable {0}".format(self))

        if variableSpecializerPath is None:
            raise Exception("VariableSpecializerPath cannot be None")

        newValue = self.dataType.generate()

        self._logger.debug("Generated value for {}: {}".format(self, newValue.tobytes()))

        variableSpecializerPath.memory.memorize(self, newValue)

        variableSpecializerPath.addResult(self, newValue)
        return [variableSpecializerPath]

    @property
    def currentValue(self):
        """
        Property (getter.setter  # type: ignore).
        The current value of the data.

        :type: :class:`bitarray`
        """
        if self.__currentValue is not None:
            return self.__currentValue.copy()
        else:
            return None

    @currentValue.setter  # type: ignore
    @typeCheck(bitarray)
    def currentValue(self, currentValue):
        if currentValue is not None:
            cv = currentValue.copy()
        else:
            cv = currentValue
        self.__currentValue = cv

    @property
    def dataType(self):
        """
        Property (getter.setter  # type: ignore).
        The type of the data.

        :type: :class:`AbstractType <netzob.Model.Vocabulary.Types.AbstractType>`
        """
        return self.__dataType

    @dataType.setter  # type: ignore
    @typeCheck(AbstractType)
    def dataType(self, dataType):
        self.__dataType = dataType
