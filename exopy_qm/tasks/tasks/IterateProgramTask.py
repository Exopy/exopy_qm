import logging
import numpy as np
from inspect import cleandoc
import time
import qm.qua
from atom.api import Float, Int, List, Typed, Str, Value, Bool, set_default
from exopy.tasks.api import InstrumentTask

class IterateProgramTask(InstrumentTask):
    """Resume a QM program and iterate it using the 'iterate' input stream. Wait until it is paused again.

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        # We assume that the program is paused and there is no data to get from the server
        self.driver.iterate()
        self.driver.wait_for_pause()
