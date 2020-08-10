from exopy.tasks.api import (InstrumentTask)
from atom.api import Int, Str, Str, set_default


class SetDigitalBufferTask(InstrumentTask):
    """ Sets the digital buffer by the given element and port
    """
    element = Str().tag(pref=True)
    digital_input = Str().tag(pref=True)
    buffer = Int().tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        self.driver.set_digital_buffer(self.element, self.digital_input, self.buffer)
