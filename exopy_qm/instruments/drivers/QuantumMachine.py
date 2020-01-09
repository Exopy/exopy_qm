import logging
import tempfile

from qm.QuantumMachinesManager import QuantumMachinesManager

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


class QuantumMachine(object):
    def __init__(self, connection_info):
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

    def set_config(self, config):
        self.qmObj = self.qmm.open_qm(config, close_other_machines=True)

    @requires_config
    def execute_program(self, prog, duration_limit, data_limit):
        self.job = self.qmObj.execute(prog,
                                      duration_limit=duration_limit,
                                      data_limit=data_limit,
                                      force_execution=True)

    def is_paused(self):
        return self.job.is_paused()

    def resume(self):
        self.job.resume()

    @requires_config
    def set_output_dc_offset_by_qe(self, element, input, offset):
        self.qmObj.set_output_dc_offset_by_element(element, input, offset)

    @requires_config
    def set_input_dc_offset_by_qe(self, element, output, offset):
        self.qmObj.set_input_dc_offset_by_element(element, output, offset)

    @requires_config
    def wait_for_all_results(self, timeout):
        self.job.wait_for_all_results(timeout)

    # TODO: Add data loss handling
    @requires_config
    def get_results(self, path=None):
        if not path:
            with tempfile.TemporaryDirectory() as tmpdirname:
                return self.job.get_results(path=tmpdirname,
                                            ignore_data_loss=True)
        else:
            return self.job.get_results(path=path, ignore_data_loss=True)

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
