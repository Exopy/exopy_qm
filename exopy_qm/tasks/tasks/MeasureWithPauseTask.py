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

    def perform(self):
        # We assume that the program is paused and there is no data to get from the server
        self.driver.resume()
        while not self.driver.is_paused():
            time.sleep(0.01)

        # check if the data are None, it happens if sever doesn't finish to average the data
        isNone = True
        while isNone:
            results = self.driver.get_results()
            OneIsNone = False
            for (name, handle) in results:
                if handle.fetch_all() is None: # check is one entry of the data is None
                    time.sleep(0.01)
                    OneIsNone = True
            if not OneIsNone: # wait all entries are not None before continue
                isNone = False



        # Create the recarray to save the data
        dt_array = []
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            values = handle.fetch_all()
            try:
                values = values['value']
            except (TypeError, IndexError):
                pass
            dt_array += [(name, values.dtype, values.shape)]
        results_recarray = np.zeros(1, dtype=dt_array)

        # Save data in the recarray
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            values = handle.fetch_all()
            try:
                values = values['value']
            except (TypeError, IndexError):
                pass
            results_recarray[name] = values
        self.write_in_database('Results', results_recarray)
