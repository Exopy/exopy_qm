from exopy.tasks.api import (InstrumentTask)
import time

class WaitForPauseAndResumeProgramTask(InstrumentTask):
    """ Resumes a paused program.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):

        t0 = time.time()
        while not self.driver.is_paused():
            #print("not paused")
            time.sleep(0.01)
            if time.time()-t0 > 60*3:
                break
            #timeout=3min
        self.driver.resume()
