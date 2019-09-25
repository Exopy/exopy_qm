from exopy.tasks.api import (InstrumentTask, validators)
from atom.api import Unicode
import numbers

EMPTY_REAL = validators.SkipEmpty(types=numbers.Real)
EMPTY_INT = validators.SkipEmpty(types=numbers.Integral)


class SetMixerCorrectionTask(InstrumentTask):
    """ Sets the mixer's correction matrix
    """
    mixer = Unicode().tag(pref=True)
    intermediate_frequency = Unicode().tag(pref=True, feval=EMPTY_INT)
    lo_frequency = Unicode().tag(pref=True, feval=EMPTY_INT)

    v00 = Unicode().tag(pref=True, feval=EMPTY_REAL)
    v01 = Unicode().tag(pref=True, feval=EMPTY_REAL)
    v10 = Unicode().tag(pref=True, feval=EMPTY_REAL)
    v11 = Unicode().tag(pref=True, feval=EMPTY_REAL)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        v00 = self.format_and_eval_string(self.v00)
        v01 = self.format_and_eval_string(self.v01)
        v10 = self.format_and_eval_string(self.v10)
        v11 = self.format_and_eval_string(self.v11)

        intermediate_frequency = self.format_and_eval_string(self.intermediate_frequency)
        lo_frequency = self.format_and_eval_string(self.lo_frequency)

        self.driver.set_mixer_correction(self.mixer, int(intermediate_frequency), int(lo_frequency),
                                         (float(v00), float(v01), float(v10), float(v11)))
