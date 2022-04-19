import ast
import importlib
import importlib.util
import logging
import numbers
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import os
import h5py
import time
from collections import OrderedDict

import qm.qua
from atom.api import List, Typed, Str, Value, Bool, set_default, Enum, Int
from exopy.tasks.api import SimpleTask, validators, InstrumentTask
from exopy.utils.atom_util import ordered_dict_from_pref, ordered_dict_to_pref
from exopy_hqc_legacy.tasks.tasks.util.save_tasks import _HDF5File
import numpy

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """ Error used to indicate a failure in the program parsing

    """
    pass

_VAL_REAL = validators.Feval(types=numbers.Real)


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
    
    # : Create the entry which contains all the data return by the OPX in a recarray
    database_entries = set_default({'Results': {}})
    
    #: Doesn't wait for the program to end if this is on
    fetch_mode = Enum('Default', 'Pause', 'PausePandas', 'Stream').tag(pref=True)
    
    #: Path to the file to stream
    stream_folder = Str(default="{default_path}").tag(pref=True)

    #: Name of the file to stream
    stream_filename = Str(default="measure.h5").tag(pref=True)

    #: Opening mode to use when saving to a file.
    stream_file_mode = Enum('New', 'Add')

    #: Currently opened file object. (File mode)
    stream_file_object = Value()

    #: Header to write at the top of the file.
    stream_header = Str().tag(pref=True)

    #: Flag indicating whether or not initialisation has been performed.
    stream_initialized = Bool(False)

    #: Data type (float16, float32, etc.)
    stream_datatype = Enum('float16', 'float32', 'float64').tag(pref=True)

    #: Compression type of the data in the HDF5 file
    stream_compression = Enum('None', 'gzip').tag(pref=True)

    #: Estimation of the number of calls of this task during the measure.
    #: This helps h5py to chunk the file appropriately
    stream_calls_estimation = Str('1').tag(pref=True, feval=_VAL_REAL)

    #: Flag indicating whether or not the data should be saved in swmr mode
    stream_swmr = Bool(True).tag(pref=True)
    
    #: Max number of data. To be used for data fetch.
    stream_n_data_max = Int(1).tag(pref=True)
    
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
        self.driver.qmm.clear_all_job_results()
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

        self.driver.clear_all_job_results()
        self.driver.set_config(config_to_set)
        self.driver.execute_program(program_to_execute)

        if self.fetch_mode=='Default':
            self.driver.wait_for_all_results()
            results = self.driver.get_results()
            report = self.driver.get_execution_report()
            if report.has_errors():
                for e in report.errors():
                    logger.warning(e)

            dt_array = []
            all_data = []
            for (name, handle) in results:
                name = self._strip_adc_name(name)
                all_data.append(handle.fetch_all(flat_struct=True))
                dt_array += [(name, all_data[-1].dtype, all_data[-1].shape)]
                self.write_in_database(f"variable_{name}", all_data[-1])
                if handle.has_dataloss():
                    logger.warning(f"{name} might have data loss")

            results_recarray = np.array([tuple(all_data)], dtype=dt_array)
            self.write_in_database('Results', results_recarray)
            
        if self.fetch_mode=='Pause':
            pass
        
        if self.fetch_mode=='PausePandas':
            self.driver.qmm.clear_all_job_results()
            self.save_stream_parameters_pandas(evaluated_parameters)

        if self.fetch_mode=='Stream':
            self.save_stream_parameters_pandas(evaluated_parameters)
            self.driver.qmm.clear_all_job_results()
            results = self.driver.get_results() #res_handle
            saved_values = {}
            new_index = {}
            prev_index = {}
            for (name, handle) in results: 
                handle.wait_for_values(1) # we wait for at least one value to appear in each stream
                prev_index[name] = 0
            # handle.wait_for_values(1) # we wait for at least one value to appear in a stream
            # all_data = []
            # while all([vec.is_processing() for vec in vec_handles]):
            #     try
            path = os.path.join(self.stream_folder, self.stream_filename)
            
            time.sleep(1)
            prev_index = 0
            flag_values_to_fetch = True
            while results.is_processing() or flag_values_to_fetch:
                saved_values = {}
                for (name, handle) in results:
                    new_index[name] = handle.count_so_far()
                min_index = min(new_index.values())
                flag_values_to_fetch = (min(new_index.values())<max(new_index.values()))
                if min_index>prev_index:
                    flag_values_to_fetch = True
                    for (name, handle) in results:
                        handle.wait_for_values(min_index-prev_index)
                        new_data = handle.fetch(slice(prev_index, min_index))["value"]
                        saved_values[name] = new_data
                    test_list = [len(v) for k,v in saved_values.items()]
                    assert(min(test_list)==max(test_list))
                    self.save_stream_results_pandas(saved_values,
                                        start=prev_index)
                    # flag_values_to_fetch = prev_index<max(new_index.values())
                    prev_index = min_index
                    #time.sleep(1e-1)
                
            report = self.driver.get_execution_report()
            if report.has_errors():
                for e in report.errors():
                    logger.warning(e)
                    
    def save_stream_results_pandas(self, saved_values ,start=0):
        full_folder_path = self.format_string(self.stream_folder)
        filename = self.format_string(self.stream_filename)
        full_path = os.path.join(full_folder_path, filename)
        store = pd.HDFStore(full_path, chunksize=1e6)
        df = pd.DataFrame(saved_values)
        df.index += start
        store.append("data", df, index=False)
        store.close()

    def save_stream_parameters_pandas(self, parameters):
        full_folder_path = self.format_string(self.stream_folder)
        filename = self.format_string(self.stream_filename)
        full_path = os.path.join(full_folder_path, filename)
        df = pd.DataFrame.from_records([parameters])
        df.to_hdf(full_path,"parameters")
            
    def save_stream_results(self, saved_values,start=0):
        full_folder_path = self.format_string(self.stream_folder)
        filename = self.format_string(self.stream_filename)
        full_path = os.path.join(full_folder_path, filename)
        for k, v in saved_values.items():
            with open(full_path+'_' + k + ".dat", "ab") as f:
                np.savetxt(f, v)

    # def save_stream_results_h5(self, saved_values):
    #     full_folder_path = self.format_string(self.stream_folder)
    #     filename = self.format_string(self.stream_filename)
    #     full_path = os.path.join(full_folder_path, filename)
    #     with h5py.File(full_path,'a') as h5f:
    #         for k, v in saved_values.items():
    #             if not k in h5f.keys():
    #                 h5f.require_dataset(k, v.shape, v.dtype, data=v,chunks=True,maxshape=(None,))
    #             else:
    #                 oldshape = h5f[k].shape
    #                 h5f[k].resize((oldshape[0]+v.shape[0],))
    #                 h5f[k][-v.shape[0]:]=v
    #                 # h5f.require_dataset(k, (v.shape), v.dtype, data=v)
    #             h5f.close()

    # def save_stream_results_h5(self, saved_values):
    #     """
    #     Appends newly acquired data to an HDF5 dataset
        
    #     Parameters
    #     ----------
    #     saved_values : dict
    #         dictionnary of saved values.

    #     Returns
    #     -------
    #     None.

    #     We are writing the data to the HDF5 dataset in append mode
    #     Copied from exopy_hqc_legacy/SaveFileHDF5Task
    #     We are purposedly shunting the exopy database and use only the HDF5 library
        
    #     """

    #     # Initialisation.
    #     if not self.stream_initialized:

    #         self._formatted_labels = []
    #         full_folder_path = self.format_string(self.stream_folder)
    #         filename = self.format_string(self.stream_filename)
    #         full_path = os.path.join(full_folder_path, filename)
    #         try:
    #             self.stream_file_object = h5py.File(full_path, 'a')
    #         except IOError:
    #             log = logging.getLogger()
    #             msg = "In {}, failed to open the specified file."
    #             log.exception(msg.format(self.name))
    #             self.root.should_stop.set()

    #         self.root.resources['files'][full_path] = self.stream_file_object

    #         f = self.stream_file_object
    #         for l, value in saved_values.items():
    #             label = self.format_string(l)
    #             if isinstance(value, numpy.ndarray):
    #                 if np.ndim(value) == 1:
    #                     names = value.dtype.names
    #                     print(names)
    #                     if names:
    #                         for m in names:
    #                             f.create_dataset(label + '_' + m,
    #                                               data=value,
    #                                               compression="gzip",
    #                                               chunks=True,
    #                                               maxshape=(None,))
    #                     else:
    #                         f.create_dataset(label,
    #                                           data=value,
    #                                           compression="gzip",
    #                                           chunks=True,
    #                                           maxshape=(None,))
    #                 else:
    #                     raise ValueError("can only save an 1D array")
    #             else:
    #                 raise ValueError("can only save an ndarray")
    #         f.attrs['header'] = self.format_string(self.stream_header)
    #         f.attrs['count_calls'] = 0
    #         if self.stream_swmr:
    #             f.swmr_mode = True
    #         f.flush()

    #         self.stream_initialized = True
        
    #     # the data has been initialized: write the data
    #     else:
        
    #         for l, value in saved_values.items():
    #             label = self.format_string(l)
    #             # self._formatted_labels.append(label)
    #             # # value = self.format_and_eval_string(v)
    #             if isinstance(value, numpy.ndarray):
    #                 if np.ndim(value) == 1:
    #                     names = value.dtype.names
    #                     if names:
    #                         for m in names:
    #                             f[label + '_' + m].resize(f[label + '_' + m].shape[0]+value.shape[0], axis=0)
    #                             f[label + '_' + m][-value.shape[0]:] = value
    #                     else:
    #                         f[label].resize(f[label + '_' + m].shape[0]+value.shape[0], axis=0)
    #                         f[label][-value.shape[0]:] = value
    #                 else:
    #                     raise ValueError("can only save 1D array")
    #             else:
    #                 raise ValueError("can only save an ndarray")

    #     f.flush()

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

    #: List of the formatted names of the entries.
    _formatted_labels = List()

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

    
    def _strip_adc_name(self, name):
        if name.endswith('_input1') or name.endswith('_input2'):
            return name[:-7]
        else:
            return name