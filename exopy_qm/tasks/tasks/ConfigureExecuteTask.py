import importlib
import importlib.util

from exopy.tasks.api import (InstrumentTask)
from atom.api import Unicode, Long, Float, Value, Typed, set_default
import sys
import os
import logging
import time

from exopy_qm.utils.dynamic_importer import *


class ConfigureExecuteTask(InstrumentTask):
    """Configures the QM, executes the QUA program and fetches the results

    This task supports parameters in both the configuration and the
    QUA program.

    The program and config files are regular python file that should
    contain at least two top-level functions:

    - get_parameters() that should return the parameters dictionnary
    of the file used to parametrize the config/program.

    - get_config(parameters)/get_program(parameters) for the
    configuration file and the program file respectively. The
    parameters argument is a dictionnary containing the values entered
    by the users and sould be converted to the appropriate python type
    before using it.

    The two files can be merged into one if wanted.

    """

    #: Path to the python configuration file
    path_to_config_file = Unicode().tag(pref=True)

    #: Module containing the configuration file
    config_module = Value()

    #: Module containing the program file
    program_module = Value()

    #: Path to the python program file
    path_to_program_file = Unicode().tag(pref=True)

    #: Maximum duration allowed for the QM
    duration_limit = Long(default=int(500000)).tag(pref=True)

    #: Maximum amount data allowed for the QM
    data_limit = Long(default=int(7000000)).tag(pref=True)

    #: Waiting time before fetching the results from the server
    wait_time = Float(default=1.0).tag(pref=True)

    #: Parameters enterd by the user for the program and config
    parameters = Typed(dict).tag(pref=True)

    #: Comments associated with the parameters
    comments = Typed(dict).tag(pref=True)

    database_entries = set_default({'variables': {}, 'raw': {}})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_module = None
        self.program_module = None
        self.parameters = {}
        self.comments = {}

    def check(self, *args, **kwargs):
        test, traceback = super(ConfigureExecuteTask,
                                self).check(*args, **kwargs)

        if not test:
            return test, traceback

        if self.config_module is None or self.program_module is None:
            msg = ('Config or program missing')
            traceback[self.get_error_path() + '-trace'] = msg

        return test, traceback

    def perform(self):
        self._update_parameters()

        config_to_set = self.config_module.get_config(self.parameters)
        program_to_execute = self.program_module.get_prog(self.parameters)

        self.driver.set_config(config_to_set)
        self.driver.execute_program(
            program_to_execute, self.duration_limit, self.data_limit)
        time.sleep(self.wait_time)
        results = self.driver.get_results()

        var_dict = {}
        for k in results.variable_results.__dict__:
            data = getattr(results.variable_results, k).data
            ts_in_ns = getattr(results.variable_results, k).ts_in_ns
            possible_data_loss = getattr(
                results.variable_results, k).possible_data_loss

            var_dict[k] = {
                "data": data,
                "ts_in_ns": ts_in_ns,
                "possible_data_loss": possible_data_loss
            }

        self.write_in_database('variables', var_dict)

        # Try to free memory as fast as possible
        var_dict = None

        raw_dict = {}
        for k in results.raw_results.__dict__:
            input1_data = getattr(results.raw_results, k).input1_data
            input2_data = getattr(results.raw_results, k).input2_data
            ts_in_ns = getattr(results.raw_results, k).ts_in_ns
            data_loss = getattr(results.raw_results, k).data_loss
            raw_dict[k] = {
                "input1_data": input1_data,
                "input2_data": input2_data,
                "ts_in_ns": ts_in_ns,
                "data_loss": data_loss
            }

        self.write_in_database('raw', raw_dict)

    def _post_setattr_path_to_program_file(self, old, new):
        if new or new != '':
            importlib.invalidate_caches()
            spec = importlib.util.spec_from_file_location(
                "", self.path_to_program_file)
            self.program_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.program_module)
        else:
            self.program_module = None

        self._update_parameters()

    def _post_setattr_path_to_config_file(self, old, new):
        if new or new != '':
            importlib.invalidate_caches()
            spec = importlib.util.spec_from_file_location(
                "", self.path_to_config_file)
            self.config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.config_module)
        else:
            self.config_module = None

        self._update_parameters()

    def _update_parameters(self):
        """Updates the parameters and attributes

        """
        params_config, params_program = {}, {}
        comments_config, comments_program = {}, {}

        if self.config_module:
            params_config, comments_config = self._parse_parameters(
                self.config_module.get_parameters())
        if self.program_module:
            params_program, comments_program = self._parse_parameters(
                self.program_module.get_parameters())

        comments_config.update(comments_program)
        self.comments = comments_config

        params_config.update(params_program)
        self.parameters = params_config

    def _parse_parameters(self, params_in):
        """Parses the parameters dictionnary enterd in the file

        Returns the parameters and comments dictionnaries

        """
        tmp_parameters = {}
        tmp_comments = {}

        for key, value in params_in.items():
            if isinstance(value, tuple) and len(value) == 2:
                # Avoid updating parameters if they already exist
                if not self.parameters or key not in self.parameters:
                    tmp_parameters[key] = str(value[0])
                else:
                    tmp_parameters[key] = self.parameters[key]
                tmp_comments[key] = str(value[1])
            else:
                if not self.parameters or key not in self.parameters:
                    tmp_parameters[key] = str(value)
                else:
                    tmp_parameters[key] = self.parameters[key]
                tmp_comments[key] = ''

        return tmp_parameters, tmp_comments
