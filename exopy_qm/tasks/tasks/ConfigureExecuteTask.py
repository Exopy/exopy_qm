import ast
import importlib
import importlib.util
import logging
from pathlib import Path
import shutil
from numpy import zeros

import qm.qua
from atom.api import List, Typed, Str, Value, Bool, set_default
from exopy.tasks.api import InstrumentTask

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """ Error used to indicate a failure in the program parsing

    """
    pass


class ConfigureExecuteTask(InstrumentTask):
    """Configures the QM, executes the QUA program and fetches the results

    This task supports parameters in both the configuration and the
    QUA program.

    The program and config files are regular python file that should
    contain at least two top-level functions:

    - get_parameters() that should return the parameters dictionary
    of the file used to parametrize the config/program.

    - get_config(parameters)/get_program(parameters) for the
    configuration file and the program file respectively. The
    parameters argument is a dictionary containing the values entered
    by the users and should be converted to the appropriate python type
    before using it.

    The two files can be merged into one if wanted.

    """

    #: Path to the python configuration file
    path_to_config_file = Str().tag(pref=True)

    #: Path to the python program file
    path_to_program_file = Str().tag(pref=True)

    #: Path to the folder where the config and program files are saved
    path_to_save = Str(default="{default_path}/configs_and_progs").tag(pref=True)

    #: Prefix used when saving the configuration and program files
    save_prefix = Str(default="{meas_id}").tag(pref=True)

    #: Parameters entered by the user for the program and config
    parameters = Typed(dict).tag(pref=True)

    #: Comments associated with the parameters
    comments = Typed(dict).tag(pref=True)

    #: Duration of the simulation in ns
    simulation_duration = Str(default="1000").tag(pref=True)

    #: Doesn't wait for the program to end if this is on
    pause_mode = Bool(False).tag(pref=True)

    # : Create the entry which contains all the data return by the OPX in a recarray
    database_entries = set_default({'Results': {}})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._config_module = None
        self._program_module = None
        self.parameters = {}
        self.comments = {}

    def check(self, *args, **kwargs):
        test, traceback = super(ConfigureExecuteTask,
                                self).check(*args, **kwargs)

        if not test:
            return test, traceback

        if self._config_module is None or self._program_module is None:
            msg = ('Config or program missing')
            traceback[self.get_error_path() + '-trace'] = msg

        for key, value in self.parameters.items():
            try:
                self.format_and_eval_string(value)
            except Exception as e:
                msg = ("Couldn't evaluate {} : {}")
                traceback[self.get_error_path() + '-trace'] = msg.format(
                    value, e)

        return test, traceback

    def perform(self):
        self._update_parameters()

        # Evaluate all parameters
        evaluated_parameters = {}
        for key, value in self.parameters.items():
            evaluated_parameters[key] = self.format_and_eval_string(value)

        config_to_set = self._config_module.get_config(evaluated_parameters)
        program_to_execute = self._program_module.get_prog(
            evaluated_parameters)

        try:
            if self.path_to_save != "":
                path_str = self.format_string(self.path_to_save)
                root_path = Path(path_str)
                if not root_path.is_dir():
                    if root_path.exists():
                        logger.warning(
                            f"Couldn't save the config and program"
                            f"to {root_path} because {root_path} is "
                            f"not a directory")
                        raise NotADirectoryError
                    else:
                        root_path.mkdir(parents=True)

                save_prefix = self.format_string(self.save_prefix)

                config_path = root_path / f"{save_prefix}_config.py"
                program_path = root_path / f"{save_prefix}_program.py"

                shutil.copyfile(self.path_to_config_file, config_path)
                shutil.copyfile(self.path_to_program_file,
                                program_path)

        except NotADirectoryError:
            pass

        self.driver.set_config(config_to_set)
        self.driver.execute_program(program_to_execute)

        if not self.pause_mode:
            self.driver.wait_for_all_results()
            results = self.driver.get_results()
            report = self.driver.get_execution_report()
            if report.has_errors():
                for e in report.errors():
                    logger.warning(e)

            for (name, handle) in results:
                # Create the recarray to save the data
                dt_array = []
                for (name, handle) in results:
                    if name.endswith('_input1') or name.endswith('_input2'):
                        name = name[:-7]
                    data = handle.fetch_all(flat_struct=True)
                    dt_array += [(name, data.dtype, data.shape)]
                    if handle.has_dataloss():
                        logger.warning(f"{name} might have data loss")
                results_recarray = zeros(1, dtype=dt_array)

                # Save data in the recarray
                for (name, handle) in results:
                    if name.endswith('_input1') or name.endswith('_input2'):
                        name = name[:-7]
                    data = handle.fetch_all(flat_struct=True)
                    self.write_in_database(f"variable_{name}", data)
                    results_recarray[name] = data
                self.write_in_database('Results', results_recarray)

    def refresh_config(self):
        self._post_setattr_path_to_config_file(self.path_to_config_file,
                                               self.path_to_config_file)

    def refresh_program(self):
        self._post_setattr_path_to_program_file(self.path_to_program_file,
                                                self.path_to_program_file)

    def simulate(self):
        """Simulate the program using the OPX

        Is always executed outside of a measurement, during editing
        """
        self._update_parameters()

        # Evaluate all parameters
        evaluated_parameters = {}
        for key, value in self.parameters.items():
            evaluated_parameters[key] = self.format_and_eval_string(value)

        config_to_set = self._config_module.get_config(evaluated_parameters)
        program_to_execute = self._program_module.get_prog(
            evaluated_parameters)

        with self.test_driver() as driver:
            driver.set_config(config_to_set)
            driver.simulate_program(program_to_execute,
                                    duration=int(self.simulation_duration)//4)

    #--------------------------Private API------------------------------#

    #: Module containing the configuration file
    _config_module = Value()

    #: Module containing the program file
    _program_module = Value()

    def _post_setattr_path_to_program_file(self, old, new):
        self._program_module = None

        if new or new != '':
            importlib.invalidate_caches()
            try:
                spec = importlib.util.spec_from_file_location(
                    "", self.path_to_program_file)
                program_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(program_module)
            except FileNotFoundError:
                logger.error(f"File {self.path_to_program_file} not found")
            except AttributeError:
                logger.error(f"File {self.path_to_program_file} is not a "
                             f"python file")
            except Exception as e:
                logger.error(f"An exception occurred when trying to import "
                             f"{self.path_to_program_file}")
                logger.error(e)
            else:
                self._program_module = program_module

        self._update_parameters()
        self._find_variables()

    def _post_setattr_path_to_config_file(self, old, new):
        self._config_module = None

        if new or new != '':
            importlib.invalidate_caches()
            try:
                spec = importlib.util.spec_from_file_location(
                    "", self.path_to_config_file)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
            except FileNotFoundError:
                logger.error(f"File {self.path_to_config_file} not found")
            except AttributeError:
                logger.error(
                    f"File {self.path_to_config_file} is not a python file")
            except Exception as e:
                logger.error(f"An exception occurred when trying to import "
                             f"{self.path_to_config_file}")
                logger.error(e)
            else:
                self._config_module = config_module

        self._update_parameters()

    def _update_parameters(self):
        """Updates the parameters and attributes

        """
        params_config, params_program = {}, {}
        comments_config, comments_program = {}, {}

        if self._config_module:
            try:
                params_config, comments_config = self._parse_parameters(
                    self._config_module.get_parameters())
            except AttributeError:
                logger.error(f"{self.path_to_config_file} needs to "
                             f"have a get_parameters function "
                             f"with no arguments.")
            except Exception as e:
                logger.error(f"An exception occurred when trying to get the "
                             f"parameters from {self.path_to_config_file}")
                logger.error(e)

        if self._program_module:
            try:
                params_program, comments_program = self._parse_parameters(
                    self._program_module.get_parameters())
            except AttributeError:
                logger.error(f"{self.path_to_program_file} needs "
                             f"to have a get_parameters function")
            except Exception as e:
                logger.error(f"An exception occurred when trying to get the "
                             f"parameters from {self.path_to_program_file}")
                logger.error(e)

        comments_config.update(comments_program)
        self.comments = comments_config

        params_config.update(params_program)
        self.parameters = params_config

    def _parse_parameters(self, params_in):
        """Parses the parameters dictionary entered in the file

        Returns the parameters and comments dictionaries

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

    def _find_variables(self):
        """Attempts to find the variables saved in a QUA program

        There are 2 types are variables: scalars and raw ADC data.
        Scalars have to be explicitly saved with a call to the save
        function whereas raw ADC data can be saved by using a string
        instead of None as the third argument of the measure function.

        New in v4: there are now streams that can be declared in the QUA
        program and saved in a special stream_processing section of the
        QUA program.

        The strategy employed here to find the name of the variables
        is

        1) Find the get_results() function

        2) Find the name of the variable returned

        3) Find a with statement that defines that variable (with the
        program() context manager)

        4) Find all instances of save(), save_all() and measure() inside
        the with statement.

        In the end, we are (almost) guaranteed to find a superset of
        all variables that will be returned by the OPX.

        """

        saved_vars = set([])
        get_results_fun, prog_name, program_node = None, None, None

        # Make sure the program is somewhat valid before parsing it
        try:
            if self._program_module:
                with open(self.path_to_program_file) as f:
                    try:
                        root = ast.parse(f.read())
                    except Exception as e:
                        logger.error(f"An error occurred when parsing "
                                     f"{self.path_to_program_file}")
                        logger.error(e)
                        raise ParseError

                for i in ast.iter_child_nodes(root):
                    if isinstance(i, ast.FunctionDef) and i.name == 'get_prog':
                        get_results_fun = i
                        break

                if not get_results_fun:
                    logger.error("Unable to find the get_prog function "
                                 "in the program file")
                    raise ParseError

                for i in ast.iter_child_nodes(get_results_fun):
                    if isinstance(i, ast.Return):
                        prog_name = i.value.id
                        break

                if not prog_name:
                    logger.error("Unable to find the name of the QUA program "
                                 "in the get_prog function")
                    raise ParseError

                for i in ast.iter_child_nodes(get_results_fun):
                    if (isinstance(i, ast.With) and i.items[0].optional_vars
                            and i.items[0].optional_vars.id == prog_name):
                        program_node = i
                        break

                if not program_node:
                    logger.error("Unable to find the QUA program definition "
                                 "in the get_prog function")
                    raise ParseError

                for i in ast.walk(program_node):
                    if isinstance(i, ast.Call) and isinstance(
                            i.func, ast.Name):
                        if i.func.id == 'save' and isinstance(i.args[1], ast.Str):
                            saved_vars.add(i.args[1].s)
                        elif (i.func.id == 'measure'
                              and isinstance(i.args[2], ast.Str)):
                            saved_vars.add(i.args[2].s)
                    elif isinstance(i, ast.Call) and isinstance(i.func, ast.Attribute) and i.func.attr in ['save', 'save_all']:
                        saved_vars.add(i.args[0].s)

        except ParseError:
            logger.error("Unable to parse the program file to find "
                         "the variable names")

        # Update the database
        de = self.database_entries.copy()
        for k in self.database_entries:
            if k.startswith('variable'):
                del de[k]

        for i in saved_vars:
            de['variable_' + i] = [0.0]

        self.database_entries = de
