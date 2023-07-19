import logging
import numpy as np
from inspect import cleandoc
import time
import qm.qua
from atom.api import Float, Int, List, Typed, Str, Value, Bool, set_default
from exopy.tasks.api import InstrumentTask

logger = logging.getLogger(__name__)


class IterateProgramTask(InstrumentTask):
    """Resume a QM program and iterate it using the 'iterate' input stream. Wait until it is paused again.

    """


    database_entries = set_default({'Results': {}})
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def check(self, *args, **kwargs):
        test, traceback = super(IterateProgramTask,
                                self).check(*args, **kwargs)

        return test, traceback

    def perform(self):
        # We assume that the program is paused and there is no data to get from the server
        self.driver.iterate()

        while not self.driver.is_paused():
            time.sleep(0.001)
            
