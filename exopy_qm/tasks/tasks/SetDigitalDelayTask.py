from exopy.tasks.api import (InstrumentTask)
from atom.api import Int, Unicode, Str, set_default


class SetDigitalDelayTask(InstrumentTask):
    """ Sets the digital delay by the given element and port
    """
    element = Unicode().tag(pref=True)
    digital_input = Unicode().tag(pref=True)
    delay = Int().tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        self.driver.set_digital_delay(self.element, self.digital_input, self.delay)
