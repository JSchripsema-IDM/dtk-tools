import os

import npyscreen
import sys

from ConfigEditionForm import ConfigEditionForm
from DefaultBlockSelectionForm import DefaultBlockSelectionForm
from dtk.utils.setupui.MainMenuForm import MainMenuForm


class SetupApplication(npyscreen.NPSAppManaged):
    """
    Main application for the dtk setup command.
    Forms available:
    - MAIN: Display the menu
    - DEFAULT_SELECTION: Form to select the default blocks
    - EDIT: Form to edit/create a block
    """

    def onStart(self):
        self.addForm('MAIN', MainMenuForm, name='dtk-tools v0.3.5')
        #self.addForm('DEFAULT_SELECTION', DefaultBlockSelectionForm, name='Configuration of the default blocks')
        self.addForm('EDIT', ConfigEditionForm, name='Block creation/edition form')

    def change_form(self, name):
        # Switch forms.  NB. Do *not* call the .edit() method directly (which
        # would lead to a memory leak and ultimately a recursion error).
        # Instead, use the method .switchForm to change forms.
        self.switchForm(name)


if __name__ == '__main__':
    # If we are on windows, resize the terminal
    if os.name == "nt":
        os.system("mode con: cols=100 lines=35")
    else:
        sys.stdout.write("\x1b[8;{rows};{cols}t".format(rows=35, cols=100))

    npyscreen.DISABLE_RESIZE_SYSTEM = True
    TestApp = SetupApplication().run()
