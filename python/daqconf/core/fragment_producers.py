# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

from rich.console import Console

import moo.otypes

moo.otypes.load_types('trigger/moduleleveltrigger.jsonnet')
moo.otypes.load_types('dfmodules/fragmentreceiver.jsonnet')
moo.otypes.load_types('dfmodules/requestreceiver.jsonnet')
moo.otypes.load_types('dfmodules/triggerrecordbuilder.jsonnet')
#
# (P. Rodrigues 2022-03-01) You would think that we need the
# load_types() line below, but when it's included, the conversion of
# app's "init" commands fails with error:
#
# AttributeError: Connection missing required field topics
#
# It's very unclear to me what's going on
#
# moo.otypes.load_types('networkmanager/nwmgr.jsonnet')

import dunedaq.trigger.moduleleveltrigger as mlt
import dunedaq.dfmodules.fragmentreceiver as frcv
import dunedaq.dfmodules.requestreceiver as rrcv
import dunedaq.dfmodules.triggerrecordbuilder as trb
# (P. Rodrigues 2022-03-01) It seems like this line shouldn't work
# without the corresponding load_types() line above, but it appears
# to. Presumably, the load_types() is being done by some other file
# (conf_utils.py in appfwk perhaps?)
import dunedaq.networkmanager.nwmgr as nwmgr

console = Console()

def set_mlt_links(the_system, mlt_app_name="trigger", verbose=False):
    """
    The MLT needs to know the full list of fragment producers in the
    system so it can populate the TriggerDecisions it creates. This
    function gets all the fragment producers in the system and adds their
    GeoIDs to the MLT's config. It assumes that the ModuleLevelTrigger
    lives in an application with name `mlt_app_name` and has the name
    "mlt".
    """
    mlt_links = []
    for producer in the_system.get_fragment_producers():
        geoid = producer.geoid
        mlt_links.append( mlt.GeoID(system=geoid.system, region=geoid.region, element=geoid.element) )
    if verbose:
        console.log(f"Adding {len(mlt_links)} links to mlt.links: {mlt_links}")
    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mgraph.reset_module_conf("mlt", mlt.ConfParams(links=mlt_links, 
                                                   dfo_connection=old_mlt_conf.dfo_connection, 
                                                   dfo_busy_connection=old_mlt_conf.dfo_busy_connection,
                                                   hsi_trigger_type_passthrough=old_mlt_conf.hsi_trigger_type_passthrough))

def remove_mlt_link(the_system, geoid, mlt_app_name="trigger"):
    """
    Remove the given geoid (which should be a dict with keys "system", "region", "element") from the list of links to request data from in the MLT.
    """
    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mlt_links = old_mlt_conf.links
    if geoid not in mlt_links:
        raise ValueError(f"GeoID {geoid} not in MLT links list")
    mlt_links.remove(geoid)
    mgraph.reset_module_conf("mlt", mlt.ConfParams(links=mlt_links, 
                                                   dfo_connection=old_mlt_conf.dfo_connection, 
                                                   dfo_busy_connection=old_mlt_conf.dfo_busy_connection,
                                                   hsi_trigger_type_passthrough=old_mlt_conf.hsi_trigger_type_passthrough))
    
def connect_fragment_producers(app_name, the_system, verbose=False):
    """Connect the data request and fragment sending queues from all of
       the fragment producers in the app with name `app_name` to the
       appropriate endpoints of the dataflow app."""
    if verbose:
        console.log(f"Connecting fragment producers in {app_name}")

    app = the_system.apps[app_name]
    producers = app.modulegraph.fragment_producers

    # Nothing to do if there are no fragment producers. Return now so we don't create unneeded RequestReceiver and FragmentSender
    if len(producers) == 0:
        return
    
    # Create fragment sender. We can do this before looping over the
    # producers because it doesn't need any settings from them
    app.modulegraph.add_module("fragment_sender",
                               plugin = "FragmentSender",
                               conf = None)

    # For each producer, we:
    # 1. Add it to the GeoID -> queue name map that is used in RequestReceiver
    # 2. Connect the relevant RequestReceiver output queue to the request input queue of the fragment producer
    # 3. Connect the fragment output queue of the producer module to the FragmentSender

    request_connection_name = f"{the_system.partition_name}.data_requests_for_{app_name}"

    from appfwk.conf_utils import geoid_raw_str, Connection, Direction, AppConnection
    
    geoid_to_queue_inst = []
    trb_geoid_to_connection = []
    request_receiver_connections = {}
    for producer in producers.values():
        geoid = producer.geoid
        queue_inst = f"data_request_q_for_{geoid_raw_str(producer.geoid)}"
        geoid_to_queue_inst.append(rrcv.geoidinst(region  = geoid.region,
                                                  element = geoid.element,
                                                  system  = geoid.system,
                                                  queueinstance = queue_inst))
        trb_geoid_to_connection.append(trb.geoidinst(region  = geoid.region,
                                                     element = geoid.element,
                                                     system  = geoid.system,
                                                     connection_name = request_connection_name))
        # It looks like RequestReceiver wants its endpoint names to
        # start "data_request_" for the purposes of checking the queue
        # type, but doesn't care what the queue instance name is (as
        # long as it matches what's in the map above), so we just set
        # the endpoint name and queue instance name to the same thing
        request_receiver_connections[queue_inst] = Connection(producer.requests_in,
                                                              queue_name = queue_inst)
        producer_mod_name, producer_endpoint_name = producer.requests_in.split(".", maxsplit=1)
        # Connect the fragment output queue to the fragment sender
        app.modulegraph.add_connection(producer.fragments_out, "fragment_sender.input_queue")
        

    the_system.network_endpoints.append(nwmgr.Connection(name=request_connection_name, topics=[], address=f"tcp://{{host_{app_name}}}:{the_system.next_unassigned_port()}"))
    
    # Create request receiver

    if verbose:
        console.log(f"Creating request_receiver for {app_name} with geoid_to_queue_inst: {geoid_to_queue_inst}, request_receiver_connections: {request_receiver_connections}")
    app.modulegraph.add_module("request_receiver",
                               plugin = "RequestReceiver",
                               conf = rrcv.ConfParams(map = geoid_to_queue_inst,
                                                      connection_name = request_connection_name),
                               connections = request_receiver_connections)
    
    # Connect request receiver to TRB output in DF app
    request_endpoint_name = f"dataflow.data_requests_for_{app_name}"
    app.modulegraph.add_endpoint("data_requests_in",
                                 internal_name = None, # Request receiver uses nwmgr, so no internal endpoint to connect to
                                 inout = Direction.IN)
    the_system.app_connections[request_endpoint_name] = AppConnection(nwmgr_connection = request_connection_name,
                                                                      receivers = [f"{app_name}.data_requests_in"],
                                                                      topics = [],
                                                                      use_nwqa = False)

    df_apps = [ (name,app) for (name,app) in the_system.apps.items() if name.startswith("dataflow") ]
    # Connect fragment sender output to TRB in DF app (via FragmentReceiver)
    fragment_endpoint_name = "{app_name}.fragments"

    for df_name, df_app in df_apps:

        fragment_connection_name = f"{the_system.partition_name}.fragments_to_{df_name}"
        if not the_system.has_network_endpoint(fragment_connection_name):
            the_system.network_endpoints.append(nwmgr.Connection(name=fragment_connection_name, topics=[], address=f"tcp://{{host_{df_name}}}:{the_system.next_unassigned_port()}"))

        df_mgraph = df_app.modulegraph
        if df_mgraph.get_module("fragment_receiver") is None:
            df_mgraph.add_module("fragment_receiver",
                                 plugin = "FragmentReceiver",
                                 conf = frcv.ConfParams(connection_name=fragment_connection_name))
            df_mgraph.add_endpoint("fragments", None,    Direction.IN)
            df_mgraph.get_module("fragment_receiver").connections["output"] = Connection("trb.data_fragment_all")

        # Add the new geoid-to-connections map to the
        # TriggerRecordBuilder.
        old_trb_conf = df_mgraph.get_module("trb").conf
        new_trb_map = old_trb_conf.map + trb_geoid_to_connection
        df_mgraph.reset_module_conf("trb", trb.ConfParams(general_queue_timeout=old_trb_conf.general_queue_timeout,
                                                          reply_connection_name = fragment_connection_name,
                                                          max_time_window = old_trb_conf.max_time_window,
                                                          mon_connection_name=old_trb_conf.mon_connection_name,
                                                          map=trb.mapgeoidconnections(new_trb_map)))

    the_system.app_connections[fragment_endpoint_name] = AppConnection(nwmgr_connection = request_connection_name,
                                                                       receivers = [f"{item[0]}.fragments" for item in df_apps ],
                                                                       topics = [],
                                                                       use_nwqa = False)


def connect_all_fragment_producers(the_system, dataflow_name="dataflow", verbose=False):
    """
    Connect all fragment producers in the system to the appropriate
    queues in the dataflow app.
    """
    for name, app in the_system.apps.items():
        if name==dataflow_name:
            continue
        connect_fragment_producers(name, the_system, verbose)
