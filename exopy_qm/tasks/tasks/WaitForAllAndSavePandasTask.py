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


class WaitForAllAndSavePandasTask(InstrumentTask):
    """Waits for all values on the OPX and saves the data from the OPX server in pandas format.

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
        test, traceback = super(WaitForAllAndSavePandasTask,
                                self).check(*args, **kwargs)

        return test, traceback

    def perform(self):

        results = self.driver.get_results() #res_handle
        saved_values = {}
        results.wait_for_all_values() # we wait for at least one value to appear in a stream
        for (name, handle) in results:
            new_data = handle.fetch_all()["value"]
            saved_values[name] = new_data
        self.save_stream_results_pandas(saved_values, start=0)
            
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
