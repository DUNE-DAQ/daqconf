
# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('dfmodules/tpstreamwriter.jsonnet')
moo.otypes.load_types('dfmodules/hdf5datastore.jsonnet')

# Import new types
import dunedaq.dfmodules.tpstreamwriter as tpsw
import dunedaq.hdf5libs.hdf5filelayout as h5fl
import dunedaq.dfmodules.hdf5datastore as hdf5ds

from appfwk.app import App, ModuleGraph
from appfwk.daqmodule import DAQModule
from appfwk.conf_utils import Direction

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100

def get_tpwriter_app(OUTPUT_PATH=".",
                     OPERATIONAL_ENVIRONMENT="swtest",
                     TPC_REGION_NAME_PREFIX="APA",
                     MAX_FILE_SIZE=4*1024*1024*1024,
                     DATA_RATE_SLOWDOWN_FACTOR=1,
                     CLOCK_SPEED_HZ=50000000,
                     HOST="localhost",
                     DEBUG=False):

    """Generate the json configuration for the readout and DF process"""

    ONE_SECOND_INTERVAL_TICKS = CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR

    modules = []

    modules += [DAQModule(name = 'tpswriter',
                          plugin = "TPStreamWriter",
                          connections = {},
                          conf = tpsw.ConfParams(tp_accumulation_interval_ticks=ONE_SECOND_INTERVAL_TICKS,
                              data_store_parameters=hdf5ds.ConfParams(
                              name="tp_stream_writer",
                              operational_environment = OPERATIONAL_ENVIRONMENT,
                              directory_path = OUTPUT_PATH,
                              max_file_size_bytes = MAX_FILE_SIZE,
                              disable_unique_filename_suffix = False,
                              filename_parameters = hdf5ds.FileNameParams(
                                  overall_prefix = "tpstream",
                                  digits_for_run_number = 6,
                                  file_index_prefix = "",
                                  digits_for_file_index = 4),
                              file_layout_parameters = h5fl.FileLayoutParams(
                                  trigger_record_name_prefix= "TimeSlice",
                                  trigger_record_header_dataset_name = "TimeSliceHeader",
                                  digits_for_trigger_number = 6,
                                  path_param_list = h5fl.PathParamList(
                                      [h5fl.PathParams(detector_group_type="TPC",
                                                       detector_group_name="TPC",
                                                       region_name_prefix=TPC_REGION_NAME_PREFIX,
                                                       element_name_prefix="Link")])))))]

    mgraph=ModuleGraph(modules)

    mgraph.add_endpoint("tpsets_into_writer", "tpswriter.tpset_source", Direction.IN)

    tpw_app = App(modulegraph=mgraph, host=HOST)

    if DEBUG:
        tpw_app.export("tpwriter_app.dot")

    return tpw_app
