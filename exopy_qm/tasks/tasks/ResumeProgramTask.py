from exopy.tasks.api import (InstrumentTask)


class ResumeProgramTask(InstrumentTask):
    """ Resumes a paused program.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        self.driver.resume()
