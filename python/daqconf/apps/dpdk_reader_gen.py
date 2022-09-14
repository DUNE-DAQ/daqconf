# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io

moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes

moo.otypes.load_types("dpdklibs/nicreader.jsonnet")

moo.otypes.load_types("readoutlibs/sourceemulatorconfig.jsonnet")
moo.otypes.load_types("readoutlibs/readoutconfig.jsonnet")
moo.otypes.load_types("readoutlibs/recorderconfig.jsonnet")

# Import new types
import dunedaq.dpdklibs.nicreader as nrc
import dunedaq.readoutlibs.sourceemulatorconfig as sec
import dunedaq.readoutlibs.readoutconfig as rconf
import dunedaq.readoutlibs.recorderconfig as bfs

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Endpoint, Direction, Queue

from detchannelmaps._daq_detchannelmaps_py import *

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100
# local clock speed Hz
CLOCK_SPEED_HZ = 50000000


def get_dpdk_reader_app(
        DRO_CONFIG=None,
        HOST='localhost',
        ENABLE_SOFTWARE_TPG=False,
        NUMBER_OF_GROUPS=2,
        NUMBER_OF_LINKS_PER_GROUP=1,
        NUMBER_OF_DATA_PRODUCERS=1,
        BASE_SOURCE_IP="10.73.139.",
        DESTINATION_IP="10.73.139.17",
        FRONTEND_TYPE='tde',
        EAL_ARGS='-l 0-1 -n 3 -- -m [0:1].0 -j',
        DEBUG=False,
):

    EAL_ARGS='-l 0-1 -n 3 -- -m [0:1].0 -j'

    number_of_dlh = NUMBER_OF_GROUPS

    DRO_CONFIG = []

    modules = []
    queues = []

    links = []
    rxcores = []
    lid = 0
    last_ip = 100
    for group in range(NUMBER_OF_GROUPS):
        offset= 0
        qlist = []
        for src in range(NUMBER_OF_LINKS_PER_GROUP):
            links.append(nrc.Link(id=lid, ip=BASE_SOURCE_IP+str(last_ip), rx_q=lid, lcore=group+1))
            qlist.append(lid)
            lid += 1
            last_ip += 1
        offset += NUMBER_OF_LINKS_PER_GROUP
        rxcores.append(nrc.LCore(lcore_id=group+1, rx_qs=qlist))

    modules += [DAQModule(name="nic_reader", plugin="NICReceiver",
                          conf=nrc.Conf(eal_arg_list=EAL_ARGS,
                                        dest_ip=DESTINATION_IP,
                                        rx_cores=rxcores,
                                        ip_sources=links),
        )]

    queues += [Queue(f"nic_reader.output_{idx}",
                     f"datahandler_{idx}.raw_input",
                     f'{FRONTEND_TYPE}_link_{idx}', 100000)
               for idx in range(number_of_dlh)]

    mgraph = ModuleGraph(modules, queues=queues)

    # for idx in range(number_of_dlh):
    #     mgraph.add_endpoint(f"requests_{idx}", f"datahandler_{idx}.request_input", Direction.IN)
    #     mgraph.add_endpoint(f"requests_{idx}", None, Direction.OUT) # Fake request endpoint

    dpdk_app = App(modulegraph=mgraph, host=HOST, name="dpdk_reader")
    return dpdk_app
