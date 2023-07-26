import logging
import tempfile
import time

from qm.QuantumMachinesManager import QuantumMachinesManager
from qm import SimulationConfig
from exopy_hqc_legacy.instruments.drivers.driver_tools import BaseInstrument

logger = logging.getLogger(__name__)


def requires_config(func):
    def wrapper(self, *args, **kwargs):
        if self.qmObj:
            return func(self, *args, **kwargs)
        else:
            logger.error(
                "Couldn't run the QUA program because no configuration was set"
            )

    return wrapper


class QuantumMachine(BaseInstrument):

    caching_permissions = {}

    def __init__(self, connection_info, caching_allowed=True,
                 caching_permissions={}, auto_open=True):
        super(QuantumMachine, self).__init__(connection_info, caching_allowed,
                                             caching_permissions, auto_open)

        self.connection_info = connection_info

        port = ""
        if connection_info[
                "gateway_port"] and connection_info["gateway_port"] != "":
            port = connection_info["gateway_port"]

        ip = ""
        if connection_info[
                "gateway_ip"] and connection_info["gateway_ip"] != "":
            ip = connection_info["gateway_ip"]

        if ip != "" and port != "":
            self.qmm = QuantumMachinesManager(host=ip, port=port)
        elif ip != "" and port == "":
            self.qmm = QuantumMachinesManager(host=ip)
        else:
            self.qmm = QuantumMachinesManager()


        self.qmObj = None
        self.job = None

    def connect(self):
        """
        Already connected in the constructor
        :return:
        """
        pass

    def connected(self):
        """Return whether or not commands can be sent to the instrument
        """
        try:
            print(self.qmObj.list_controllers())
        except Exception:
            return False

        return True

    def close_connection(self):
        if self.qmObj:
            self.qmObj.close()

    def clear_all_job_results(self):
        self.qmm.clear_all_job_results()

    def set_config(self, config):
        self.qmObj = self.qmm.open_qm(config, close_other_machines=True)

    @requires_config
    def execute_program(self, prog, duration_limit=0, data_limit=0):
        """Create a job on the OPX to execute a program.

        The duration_limit and data_limit arguments specify the
        maximum time and data size that the job can use before getting
        stopped by the server. Those limits are disabled by default.

        """
        self.job = self.qmObj.execute(prog,
                                      duration_limit=duration_limit,
                                      data_limit=data_limit,
                                      force_execution=True)

    @requires_config
    def simulate_program(self, prog, duration):
        """ Simulate the program on the OPX

        The duration parameter specifies the number of FPGA cycles
        of the simulation (4ns/cycle).
        This functions opens a matplotlib popup with the results.
        """
        self.job = self.qmObj.simulate(prog, SimulationConfig(
            duration=duration,
            include_analog_waveforms=True))
        samples = self.job.get_simulated_samples()
        samples.con1.plot(digital_ports=(0,))
        import matplotlib.pyplot as plt
        plt.show()

    def is_paused(self):
        return self.job.is_paused()

    def resume(self):
        self.job.resume()

    def wait_for_pause(self):
        """waits for the program to be paused
        """
        while not self.is_paused():
            time.sleep(0.01)
        
    def iterate(self):
        """Iterates the program by resuming it and feeding True to the input sting 'iterate' 
        """
        self.job.resume()
        self.job.insert_input_stream('iterate', True)

    def finish(self):
        """Finishes the program by resuming it and feeding False to the input sting 'iterate'
          """
        self.job.resume()
        self.job.insert_input_stream('iterate', False)

    @requires_config
    def set_output_dc_offset_by_qe(self, element, input, offset):
        self.qmObj.set_output_dc_offset_by_element(element, input, offset)

    @requires_config
    def set_input_dc_offset_by_qe(self, element, output, offset):
        self.qmObj.set_input_dc_offset_by_element(element, output, offset)

    @requires_config
    def wait_for_all_results(self, ):
        """Wait for the current job to be completed.
        """
        self.job.result_handles.wait_for_all_values()

    @requires_config
    def get_results(self, path=None):
        return self.job.result_handles

    @requires_config
    def get_execution_report(self, path=None):
        return self.job.execution_report()

    @requires_config
    def set_io_values(self, io1_value, io2_value):
        self.qmObj.set_io_values(io1_value, io2_value)

    @requires_config
    def get_io_values(self):
        return self.qmObj.get_io_values()

    @requires_config
    def set_mixer_correction(self, mixer, intermediate_frequency, lo_frequency,
                             values):
        self.qmObj.set_mixer_correction(mixer, intermediate_frequency,
                                        lo_frequency, values)

    @requires_config
    def set_intermediate_frequency(self, qe, intermediate_frequency):
        self.qmObj.set_intermediate_frequency(qe, intermediate_frequency)

    @requires_config
    def set_digital_delay(self, qe, digital_input, delay):
        self.qmObj.set_digital_delay(qe, digital_input, delay)

    @requires_config
    def set_digital_buffer(self, qe, digital_input, buffer):
        self.qmObj.set_digital_buffer(qe, digital_input, buffer)
