# -*- coding: utf-8 -*-

#+---------------------------------------------------------------------------+
#|          01001110 01100101 01110100 01111010 01101111 01100010            |
#|                                                                           |
#|               Netzob : Inferring communication protocols                  |
#+---------------------------------------------------------------------------+
#| Copyright (C) 2011 Georges Bossert and Frédéric Guihéry                   |
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
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+ 
#| Global Imports
#+---------------------------------------------------------------------------+
import uuid
from datetime import datetime

#+---------------------------------------------------------------------------+
#| Local Imports
#+---------------------------------------------------------------------------+
from netzob.Common.Field import Field
from netzob.Common.ProjectConfiguration import ProjectConfiguration
from netzob.Common.ImportedTrace import ImportedTrace
from netzob.Common.Symbol import Symbol

#+---------------------------------------------------------------------------+
#| AbstractImporter :
#|     Mother class which provides common methods too any kind of importers
#+---------------------------------------------------------------------------+
class AbstractImporter:
    
    def __init__(self, type):     
        self.type = type
        
    #+-----------------------------------------------------------------------+
    #| saveMessagesInProject :
    #|   Add a selection of messages to an existing project
    #|   it also saves them in the workspace
    #+-----------------------------------------------------------------------+
    def saveMessagesInProject(self, workspace, project, messages):
        
        # We create a symbol dedicated for this
        symbol = Symbol(uuid.uuid4(), self.type, project)
        for message in messages :
            symbol.addMessage(message)
        
        # We create a default field for the symbol
        symbol.addField(Field.createDefaultField())
        # and register the symbol in the vocabulary of the project
        project.getVocabulary().addSymbol(symbol)
        # Add the environmental dependencies to the project
        project.getConfiguration().setVocabularyInferenceParameter(ProjectConfiguration.VOCABULARY_ENVIRONMENTAL_DEPENDENCIES,
                                                                   self.envDeps.getEnvData())        
        # Computes current date
        date = datetime.now()
        description = "No description (yet not implemented)"
        
        # Now we also save the messages in the workspace
        trace = ImportedTrace(uuid.uuid4(), date, type, description, project.getName())
        for message in messages :
            trace.addMessage(message)
        workspace.addImportedTrace(trace)
    