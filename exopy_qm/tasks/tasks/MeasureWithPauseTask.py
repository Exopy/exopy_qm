import logging
import numpy as np
from inspect import cleandoc
import time
import qm.qua
from atom.api import Float, Int, List, Typed, Str, Value, Bool, set_default
from exopy.tasks.api import InstrumentTask

logger = logging.getLogger(__name__)


class MeasureWithPauseTask(InstrumentTask):
    """Resume a QM program which is paused, wait to is paused again and get the data from the OPX server.

    """


    database_entries = set_default({'Results': {}})
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def check(self, *args, **kwargs):
        test, traceback = super(MeasureWithPauseTask,
                                self).check(*args, **kwargs)

        return test, traceback

    # def perform(self):
    #     # We assume that the program is paused and there is no data to get from the server
    #     self.driver.resume()
    #     while not self.driver.is_paused():
    #         print("not paused")
    #         time.sleep(0.01)

    #     # check if the data are None: it happens if the server hasn't finished averaging the data
    #     while True:
    #         results = self.driver.get_results()
    #         one_is_none = False
    #         for (name, handle) in results:
    #             if handle.fetch_all() is None: # check is one entry of the data is None
    #                 time.sleep(0.01)
    #                 one_is_none = True
    #         if not one_is_none: # wait for all entries to be not None before continuing
    #             break
    #         print("some entries are None")

    def perform(self):
        # We assume that the program is paused and there is no data to get from the server
        
        while not self.driver.is_paused():
            #print("not paused")
            time.sleep(0.01)
        self.driver.resume()
        # check if the data are None: it happens if the server hasn't finished averaging the data
        results = self.driver.get_results()
        for (name, handle) in results: # We get one data for all the names
            handle.wait_for_values(1)

        # Create the recarray to save the data
        dt_array = []
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            data = handle.fetch_all(flat_struct=True)
            dt_array += [(name, data.dtype, data.shape)]
            if handle.has_dataloss():
                logger.warning(f"{name} might have data loss")
        results_recarray = np.zeros(1, dtype=dt_array)

        # Save data in the recarray
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            data = handle.fetch_all(flat_struct=True)
            results_recarray[name] = data
        self.write_in_database('Results', results_recarray)
