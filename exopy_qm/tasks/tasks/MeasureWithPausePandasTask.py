import logging
import numpy as np
from inspect import cleandoc
import time
import qm.qua
from atom.api import Float, Int, List, Typed, Str, Value, Bool, set_default, Enum
from exopy.tasks.api import InstrumentTask
import os
import pandas as pd

logger = logging.getLogger(__name__)


class MeasureWithPausePandasTask(InstrumentTask):
    """Resume a QM program which is paused, wait to is paused again and get the data from the OPX server.

    """
    #: Path to the file to stream
    stream_folder = Str(default="{default_path}").tag(pref=True)

    #: Name of the file to stream
    stream_filename = Str(default="{meas_name}_{meas_id}.h5").tag(pref=True)

    #: Opening mode to use when saving to a file.
    stream_file_mode = Enum('New', 'Add')

    #: Currently opened file object. (File mode)
    stream_file_object = Value()

    database_entries = set_default({'Results': {}})
    #: Max number of data. To be used for data fetch.
    n_data = Int(1).tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def check(self, *args, **kwargs):
        test, traceback = super(MeasureWithPausePandasTask,
                                self).check(*args, **kwargs)

        return test, traceback

    def perform(self):

        # We assume that the program is paused and there is no data to get from the server
        while not self.driver.is_paused(): #We wait for the first pause statement
            #print("not paused")
            time.sleep(0.01)
        self.driver.resume()    
        # Evaluate all parameters

        #self.driver.qmm.clear_all_job_results()
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
        
        #time.sleep(1)
        prev_index = 0
        flag_values_to_fetch = True
        while results.is_processing() or flag_values_to_fetch:
            saved_values = {}
            for (name, handle) in results:
                new_index[name] = handle.count_so_far()
            min_index = min(new_index.values())
            flag_values_to_fetch = (min(new_index.values())<max(new_index.values()))
            #print("indices",min_index, prev_index, saved_values)
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
                prev_index = min_index
            if self.driver.is_paused():
                break
            # print("processing", results.is_processing(), "values to fetch", flag_values_to_fetch, "is paused", self.driver.is_paused())
                #time.sleep(1e-1)
            
        report = self.driver.get_execution_report()
        if report.has_errors():
            for e in report.errors():
                logger.warning(e)

        # for i in range(3):
        #     results = self.driver.get_results()
        #     for (name, handle) in results: # We get one data for all the names
        #         handle.wait_for_values(1)
        #     # save all data
        #     self.driver.resume()

        # # check if the data are None: it happens if the server hasn't finished averaging the data
        # while True:
        #     results = self.driver.get_results()
        #     one_is_none = False
        #     for (name, handle) in results:
        #         if handle.fetch_all() is None: # check is one entry of the data is None
        #             time.sleep(0.01)
        #             one_is_none = True
        #     if not one_is_none: # wait for all entries to be not None before continuing
        #         break
        #     print("some entries are None")

        # Create the recarray to save the data

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
        if pd.read_hdf(full_path,"parameters") is None:
            df.to_hdf(full_path,"parameters")
