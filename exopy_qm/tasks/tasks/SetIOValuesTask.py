from exopy.tasks.api import (InstrumentTask)
from atom.api import Unicode, Bool

from exopy_qm.utils.utils import is_int, is_float


class SetIOValuesTask(InstrumentTask):
    """ Sets the IO values
    """
    set_io_1 = Bool(True).tag(pref=True)
    io_1_value = Unicode().tag(pref=True)

    set_io_2 = Bool(True).tag(pref=True)
    io_2_value = Unicode().tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.io_1_value = ""
        self.io_2_value = ""

    def perform(self):
        if self.set_io_1 and self.io_2_value:
            self.driver.set_io_values(self.__get_io1_value(), self.__get_io2_value())
        elif self.set_io_1:
            self.driver.set_io_values(self.__get_io1_value(), None)
        elif self.set_io_2:
            self.driver.set_io_values(None, self.__get_io2_value())

    @staticmethod
    def __get_value(x):
        if is_int(x):
            return int(x)
        elif is_float(x):
            return float(x)
        elif x.lower() == "true":
            return True
        elif x.lower() == "false":
            return False
        else:
            return None

    def __get_io1_value(self):
        val = self.__get_value(self.io_1_value)
        if val is None:
            raise Exception("Invalid IO1 value")
        return val

    def __get_io2_value(self):
        val = self.__get_value(self.io_2_value)
        if val is None:
            raise Exception("Invalid IO2 value")
        return val
