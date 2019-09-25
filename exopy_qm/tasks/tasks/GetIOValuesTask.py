from exopy.tasks.api import (InstrumentTask)
from atom.api import Bool, set_default


class GetIOValuesTask(InstrumentTask):
    """ Gets the IO values
    """
    get_io_1 = Bool(True).tag(pref=True)

    get_io_2 = Bool(True).tag(pref=True)

    database_entries = set_default({'IO1': {}, 'IO2': {}})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        io_values = self.driver.get_io_values()
        if self.get_io_1:
            self.write_in_database('IO1', io_values[0])
        if self.get_io_2:
            self.write_in_database('IO2', io_values[0])
