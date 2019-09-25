import importlib

from exopy.tasks.api import (InstrumentTask)
from atom.api import Unicode, Long
import sys
import os
import shutil


from exopy_qm.utils.dynamic_importer import *


class ExecuteProgramTask(InstrumentTask):
    """ Executes a qua program.
    """
    path_to_program_file = Unicode().tag(pref=True)
    duration_limit = Long(default=int(1000)).tag(pref=True)
    data_limit = Long(default=int(20000)).tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        directory = get_directory_from_path(self.path_to_program_file)
        module_name = get_module_name_from_path(self.path_to_program_file)

        sys.path.append(directory)

        module_with_program = importlib.import_module(module_name)
        module_with_program = importlib.reload(module_with_program)

        program_to_execute = module_with_program.get_prog()

        self._save_program_and_config()

        self.driver.execute_program(program_to_execute, self.duration_limit, self.data_limit)

    def _save_program_and_config(self):
        measure_name = self.get_from_database('meas_name')
        measure_id = self.get_from_database('meas_id')
        path = self.root.default_path
        prog_file_name = os.path.join(path, f"{measure_name}_{measure_id}.program.py")
        config_file_name = os.path.join(path, f"{measure_name}_{measure_id}.config.py")

        shutil.copy2(self.path_to_program_file, prog_file_name)
        shutil.copy2(self.driver.get_config_path(), config_file_name)
