from simtools.Managers.WorkItemManager import WorkItemManager
from simtools.SetupParser import SetupParser
from simtools.AssetManager.FileList import FileList

wi_name = "SSMT Analysis"
command = "python run_analysis.py"
user_files = FileList(root='files')

if __name__ == "__main__":
    SetupParser.default_block = 'HPC'
    SetupParser.init()

    wim = WorkItemManager(item_name=wi_name, command=command, user_files=user_files)
    wim.execute(True)