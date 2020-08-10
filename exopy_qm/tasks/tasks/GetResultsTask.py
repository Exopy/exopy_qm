import gzip
import json

from exopy.tasks.api import (InstrumentTask)
from atom.api import Float, Str, Str, set_default
from qm.qua import *


class GetResultsTask(InstrumentTask):
    """ Retrieves the variable results from the opx into the exopy database under 'variables'.
     The returned value will be a dictionary, with the key being the name of the variable saved in qua and the value
     being a dictionary with the saved variable data (see the qua documentation for more information)
    """

    database_entries = set_default({'variables': {}, 'raw': {}})

    results_file_path = Str().tag(pref=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def perform(self):
        results = self.driver.get_results()

        var_dict = {}
        for k in results.variable_results.__dict__:
            data = getattr(results.variable_results, k).data
            ts_in_ns = getattr(results.variable_results, k).ts_in_ns
            possible_data_loss = getattr(results.variable_results, k).possible_data_loss

            var_dict[k] = {
                "data": data,
                "ts_in_ns": ts_in_ns,
                "possible_data_loss": possible_data_loss
            }

        self.write_in_database('variables', var_dict)

        raw_dict = {}
        for k in results.raw_results.__dict__:
            input1_data = getattr(results.raw_results, k).input1_data
            input2_data = getattr(results.raw_results, k).input2_data
            ts_in_ns = getattr(results.raw_results, k).ts_in_ns
            data_loss = getattr(results.raw_results, k).data_loss
            raw_dict[k] = {
                "input1_data": input1_data,
                "input2_data": input2_data,
                "ts_in_ns": ts_in_ns,
                "data_loss": data_loss
            }

        self.write_in_database('raw', raw_dict)

        all_dict = {'raw': raw_dict, 'variables': var_dict}  # 1. data

        json_str = json.dumps(all_dict)  # 2. json string
        json_bytes = json_str.encode('utf-8')  # 3. UTF8 bytes

        with gzip.GzipFile(self.results_file_path, 'w') as writer:  # 4. gzip
            writer.write(json_bytes)

        # To read the zipped file
        # with gzip.GzipFile(jsonfilename, 'r') as fin:  # 4. gzip
        #     json_bytes = fin.read()  # 3. bytes (i.e. UTF-8)
        #
        # json_str = json_bytes.decode('utf-8')  # 2. string (i.e. JSON)
        # data = json.loads(json_str)  # 1. data
