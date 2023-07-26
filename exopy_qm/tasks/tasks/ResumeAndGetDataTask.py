import logging
import numpy as np
from inspect import cleandoc
import time
import qm.qua
from atom.api import Float, Int, List, Typed, Str, Value, Bool, set_default
from exopy.tasks.api import InstrumentTask

logger = logging.getLogger(__name__)


class ResumeAndGetDataTask(InstrumentTask):
    """Resume a QM program and finishes it using the 'iterate' input stream.

    """


    database_entries = set_default({'Results': {}})
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def check(self, *args, **kwargs):
        test, traceback = super(ResumeAndGetDataTask,
                                self).check(*args, **kwargs)

        return test, traceback

    def perform(self):
        # We assume that the program is paused for the last time
        self.driver.resume()

        self.driver.wait_for_all_results()
        results = self.driver.get_results()
        report = self.driver.get_execution_report()
        if report.has_errors():
            for e in report.errors():
                logger.warning(e)

        dt_array = []
        all_data = []
        for (name, handle) in results:
            if name.endswith('_input1') or name.endswith('_input2'):
                name = name[:-7]
            all_data.append(handle.fetch_all(flat_struct=True))
            dt_array += [(name, all_data[-1].dtype, all_data[-1].shape)]
            if handle.has_dataloss():
                logger.warning(f"{name} might have data loss")

        results_recarray = np.array([tuple(all_data)], dtype=dt_array)
        self.write_in_database('Results', results_recarray)