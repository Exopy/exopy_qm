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

        if not test:
            return test, traceback
        
        
        return test, traceback

    def perform(self):
        #assume the program is in paused and there are no data to get from the server
        self.driver.resume()
        while self.driver.is_paused()==False:
            time.sleep(0.01)
        results = self.driver.get_results()
        
        #Create the recarray to save the data
        dt_array = []
        for (name, handle) in results:
                if name.endswith('_input1') or name.endswith('_input2'):
                    name = name[:-7]
                values = handle.fetch_all()
                dt_array += [(name, values.dtype,values.shape)]
        results_recarray = np.zeros(1, dtype=dt_array)

        #Save date in the recarray
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            values = handle.fetch_all()
            if type(values) is dict and 'value' in values:
                values = values['value']
            results_recarray[name] = values
        self.write_in_database('Results',results_recarray )

      