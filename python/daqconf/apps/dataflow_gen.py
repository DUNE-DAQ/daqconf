
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
moo.otypes.load_types('dfmodules/fragmentreceiver.jsonnet')
moo.otypes.load_types('dfmodules/triggerdecisionreceiver.jsonnet')
moo.otypes.load_types('networkmanager/nwmgr.jsonnet')


# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dfmodules.datawriter as dw
import dunedaq.hdf5libs.hdf5filelayout as h5fl
import dunedaq.dfmodules.hdf5datastore as hdf5ds
import dunedaq.dfmodules.fragmentreceiver as frcv
import dunedaq.dfmodules.triggerdecisionreceiver as tdrcv
import dunedaq.networkmanager.nwmgr as nwmgr

from appfwk.utils import acmd, mcmd, mrccmd, mspec
from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction, data_request_endpoint_name

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100

def get_dataflow_app(HOSTIDX=0,
                     OUTPUT_PATH=".",
                     PARTITION="UNKNOWN",
                     OPERATIONAL_ENVIRONMENT="swtest",
                     TPC_REGION_NAME_PREFIX="APA",
                     MAX_FILE_SIZE=4*1024*1024*1024,
                     MAX_TRIGGER_RECORD_WINDOW=0,
                     HOST="localhost",
                     HAS_DQM=False,
                     DEBUG=False):

    """Generate the json configuration for the readout and DF process"""

    modules = []

    modules += [DAQModule(name = 'trb',
                          plugin = 'TriggerRecordBuilder',
                          conf = trb.ConfParams(general_queue_timeout=QUEUE_POP_WAIT_MS,
                                                reply_connection_name = "",
                                                max_time_window=MAX_TRIGGER_RECORD_WINDOW,
                                                map=trb.mapgeoidconnections([]))), # We patch this up in connect_fragment_producers
                DAQModule(name = 'datawriter',
                       plugin = 'DataWriter',
                       conf = dw.ConfParams(decision_connection=f"trigger_decision_{HOSTIDX}",
                           data_store_parameters=hdf5ds.ConfParams(
                               name="data_store",
                               operational_environment = OPERATIONAL_ENVIRONMENT,
                               directory_path = OUTPUT_PATH,
                               max_file_size_bytes = MAX_FILE_SIZE,
                               disable_unique_filename_suffix = False,
                               filename_parameters = hdf5ds.FileNameParams(
                                   overall_prefix = OPERATIONAL_ENVIRONMENT,
                                   digits_for_run_number = 6,
                                   file_index_prefix = "",
                                   digits_for_file_index = 4),
                               file_layout_parameters = h5fl.FileLayoutParams(
                                   record_name_prefix= "TriggerRecord",
                                   digits_for_record_number = 5,
                                   path_param_list = h5fl.PathParamList(
                                       [h5fl.PathParams(detector_group_type="TPC",
                                                        detector_group_name="TPC",
                                                        region_name_prefix=TPC_REGION_NAME_PREFIX,
                                                        element_name_prefix="Link"),
                                        h5fl.PathParams(detector_group_type="PDS",
                                                        detector_group_name="PDS"),
                                        h5fl.PathParams(detector_group_type="NDLArTPC",
                                                        detector_group_name="NDLArTPC"),
                                        h5fl.PathParams(detector_group_type="DataSelection",
                                                        detector_group_name="Trigger")])))))]

    mgraph=ModuleGraph(modules)

    mgraph.connect_modules("trb.trigger_record_output", "datawriter.trigger_record_input", "trigger_records")
    mgraph.add_endpoint(f"trigger_decision_{HOSTIDX}", "trb.trigger_decision_input", Direction.IN)
    mgraph.add_endpoint("triginh", "datawriter.token_output", Direction.OUT)
    if HAS_DQM:
        mgraph.add_endpoint(f"trmon_dqm2df_{HOSTIDX}", "trb.mon_connection", Direction.IN)
        mgraph.add_endpoint(f"tr_df2dqm_{HOSTIDX}", None, Direction.OUT)

    df_app = App(modulegraph=mgraph, host=HOST)

    if DEBUG:
        df_app.export("dataflow_app.dot")

    return df_app
