from exopy.tasks.api import (InstrumentTask, validators)
from atom.api import Unicode
import numbers
EMPTY_REAL = validators.SkipEmpty(types=numbers.Real)
EMPTY_INT = validators.SkipEmpty(types=numbers.Integral)


class SetOutputDcOffsetByQeTask(InstrumentTask):
    """ Sets the output dc offset of the given element and port by the given offset value.
    """
    element = Unicode().tag(pref=True)
    input = Unicode().tag(pref=True)
    offset = Unicode().tag(pref=True, feval=EMPTY_REAL)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        offset = self.format_and_eval_string(self.offset)

        self.driver.set_output_dc_offset_by_qe(self.element, self.input, float(offset))
