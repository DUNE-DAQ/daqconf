
# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('dfmodules/triggerrecordbuilder.jsonnet')
moo.otypes.load_types('dfmodules/datawriter.jsonnet')
moo.otypes.load_types('dfmodules/hdf5datastore.jsonnet')


# Import new types
import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dfmodules.datawriter as dw
import dunedaq.hdf5libs.hdf5filelayout as h5fl
import dunedaq.dfmodules.hdf5datastore as hdf5ds

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100

def get_dataflow_app(HOSTIDX=0,
                     OUTPUT_PATHS=["."],
                     APP_NAME="dataflow0",
                     OPERATIONAL_ENVIRONMENT="swtest",
                     DATA_STORE_MODE='all-per-file',
                     MAX_FILE_SIZE=4*1024*1024*1024,
                     MAX_TRIGGER_RECORD_WINDOW=0,
                     MAX_EXPECTED_TR_SEQUENCES=1,
                     TOKEN_COUNT=10,
                     TRB_TIMEOUT=200,
                     HOST="localhost",
                     HAS_DQM=False,
                     HARDWARE_MAP='',
                     DEBUG=False):

    """Generate the json configuration for the readout and DF process"""

    modules = []

    if DEBUG: print(f"dataflow{HOSTIDX}: Adding TRB instance")
    modules += [DAQModule(name = 'trb',
                          plugin = 'TriggerRecordBuilder',
                          conf = trb.ConfParams(general_queue_timeout=QUEUE_POP_WAIT_MS,
                                                reply_connection_name = "",
                                                max_time_window=MAX_TRIGGER_RECORD_WINDOW,
                                                source_id = HOSTIDX,
                                                trigger_record_timeout_ms=TRB_TIMEOUT))]
                      
    for i in range(len(OUTPUT_PATHS)):     
        if DEBUG: print(f"dataflow{HOSTIDX}: Adding datawriter{i} instance")                 
        modules += [DAQModule(name = f'datawriter_{i}',
                       plugin = 'DataWriter',
                       conf = dw.ConfParams(decision_connection=f"trigger_decision_{HOSTIDX}",
                           data_store_parameters=hdf5ds.ConfParams(
                               name="data_store",
                               operational_environment = OPERATIONAL_ENVIRONMENT,
                               mode = DATA_STORE_MODE,
                               directory_path = OUTPUT_PATHS[i],
                               max_file_size_bytes = MAX_FILE_SIZE,
                               disable_unique_filename_suffix = False,
                               hardware_map=HARDWARE_MAP,
                               filename_parameters = hdf5ds.FileNameParams(
                                   overall_prefix = OPERATIONAL_ENVIRONMENT,
                                   digits_for_run_number = 6,
                                   file_index_prefix = "",
                                   digits_for_file_index = 4,
                                   writer_identifier = f"{APP_NAME}_datawriter_{i}"),
                               file_layout_parameters = h5fl.FileLayoutParams(
                                   record_name_prefix= "TriggerRecord",
                                   digits_for_record_number = 5,
                                   path_param_list = h5fl.PathParamList(
                                       [h5fl.PathParams(detector_group_type="Detector_Readout",
                                                        detector_group_name="TPC",
                                                        element_name_prefix="Link"),
                                        h5fl.PathParams(detector_group_type="Detector_Readout",
                                                        detector_group_name="PDS"),
                                        h5fl.PathParams(detector_group_type="Detector_Readout",
                                                        detector_group_name="NDLArTPC"),
                                        h5fl.PathParams(detector_group_type="Detector_Readout",
                                                        detector_group_name="NDLArPDS"),
                                        h5fl.PathParams(detector_group_type="Trigger",
                                                        detector_group_name="DataSelection",
                                                        digits_for_element_number=5),
                                        h5fl.PathParams(detector_group_type="HW_Signals_Interface",
                                                        detector_group_name="HSI")
                                    ])))))]

    mgraph=ModuleGraph(modules)

    mgraph.add_endpoint(f"trigger_decision_{HOSTIDX}", "trb.trigger_decision_input", "TriggerDecision", Direction.IN)

    queue_size_based_on_number_of_sequences = max(10, int(MAX_EXPECTED_TR_SEQUENCES * TOKEN_COUNT * 1.1))
    for i in range(len(OUTPUT_PATHS)):
        mgraph.connect_modules("trb.trigger_record_output", f"datawriter_{i}.trigger_record_input","TriggerRecord", "trigger_records",
                               queue_size_based_on_number_of_sequences)
        mgraph.add_endpoint("triginh", f"datawriter_{i}.token_output", "TriggerDecisionToken", Direction.OUT, toposort=True)

    if HAS_DQM:
        mgraph.add_endpoint(f"trmon_dqm2df_{HOSTIDX}", "trb.mon_connection", "TRMonRequest", Direction.IN)
        mgraph.add_endpoint(f"tr_df2dqm_{HOSTIDX}", None, "TriggerRecord", Direction.OUT)

    df_app = App(modulegraph=mgraph, host=HOST)

    return df_app
