# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

from rich.console import Console

import moo.otypes
import re

moo.otypes.load_types('trigger/moduleleveltrigger.jsonnet')
moo.otypes.load_types('dfmodules/fragmentreceiver.jsonnet')
moo.otypes.load_types('dfmodules/requestreceiver.jsonnet')
moo.otypes.load_types('dfmodules/triggerrecordbuilder.jsonnet')

import dunedaq.trigger.moduleleveltrigger as mlt
import dunedaq.dfmodules.fragmentreceiver as frcv
import dunedaq.dfmodules.requestreceiver as rrcv
import dunedaq.dfmodules.triggerrecordbuilder as trb

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
#    app.modulegraph.add_module("fragment_sender",
#                               plugin = "FragmentSender",
#                               conf = None)

    # For each producer, we:
    # 1. Add it to the GeoID -> queue name map that is used in RequestReceiver
    # 2. Connect the relevant RequestReceiver output queue to the request input queue of the fragment producer
    # 3. Connect the fragment output queue of the producer module to the FragmentSender

    request_connection_name = f"data_requests_for_{app_name}"

    from daqconf.core.conf_utils import geoid_raw_str, Direction
    
    geoid_to_queue_inst = []
    trb_geoid_to_connection = []

    for producer in producers.values():
        geoid = producer.geoid
        queue_inst = f"data_request_q_for_{geoid_raw_str(producer.geoid)}"
        geoid_to_queue_inst.append(rrcv.geoidinst(region  = geoid.region,
                                                  element = geoid.element,
                                                  system  = geoid.system,
                                                  connection_uid = queue_inst))
        trb_geoid_to_connection.append(trb.geoidinst(region  = geoid.region,
                                                     element = geoid.element,
                                                     system  = geoid.system,
                                                     connection_uid = request_connection_name))
        
        # Connect the fragment output queue to the fragment sender
#        app.modulegraph.connect_modules(producer.fragments_out, "fragment_sender.input_queue")
        
    # Create request receiver

    if verbose:
        console.log(f"Creating request_receiver for {app_name} with geoid_to_queue_inst: {geoid_to_queue_inst}")
    app.modulegraph.add_module("request_receiver",
                               plugin = "RequestReceiver",
                               conf = rrcv.ConfParams(map = geoid_to_queue_inst ))

    
    for producer in producers.values():
        # It looks like RequestReceiver wants its endpoint names to
        # start "data_request_" for the purposes of checking the queue
        # type, but doesn't care what the queue instance name is (as
        # long as it matches what's in the map above), so we just set
        # the endpoint name and queue instance name to the same thing
        queue_inst = f"data_request_q_for_{geoid_raw_str(producer.geoid)}"
        app.modulegraph.connect_modules(f"request_receiver.data_request_{geoid_raw_str(producer.geoid)}", producer.requests_in, queue_inst)

                               
    # Connect request receiver to TRB output in DF app
    app.modulegraph.add_endpoint(request_connection_name,
                                 internal_name = "request_receiver.input", 
                                 inout = Direction.IN)
                               
    df_apps = [ (name,app) for (name,app) in the_system.apps.items() if name.startswith("dataflow") ]
    # Connect fragment sender output to TRB in DF app (via FragmentReceiver)
    fragment_endpoint_name = "{app_name}.fragments"

    for df_name, df_app in df_apps:
        fragment_connection_name = f"fragments_to_{df_name}"
        app.modulegraph.add_endpoint(fragment_connection_name, None, Direction.OUT)
        df_mgraph = df_app.modulegraph
        df_mgraph.add_endpoint(fragment_connection_name, "trb.data_fragment_all", Direction.IN, toposort=True)            
        df_mgraph.add_endpoint(request_connection_name, f"trb.request_output_{app_name}", Direction.OUT)

        # Add the new geoid-to-connections map to the
        # TriggerRecordBuilder.
        old_trb_conf = df_mgraph.get_module("trb").conf
        new_trb_map = old_trb_conf.map + trb_geoid_to_connection
        df_mgraph.reset_module_conf("trb", trb.ConfParams(general_queue_timeout=old_trb_conf.general_queue_timeout,
                                                          reply_connection_name = fragment_connection_name,
                                                          max_time_window = old_trb_conf.max_time_window,
                                                          trigger_record_timeout_ms = old_trb_conf.trigger_record_timeout_ms,
                                                          map=trb.mapgeoidconnections(new_trb_map)))
                          
    dqm_apps = [ (name,app) for (name,app) in the_system.apps.items() if re.match("dqm\d+-ru", name) ]

    for dqm_name, dqm_app in dqm_apps:
        fragment_connection_name = f"fragments_to_{dqm_name}"
        app.modulegraph.add_endpoint(fragment_connection_name, None, Direction.OUT)
        dqm_mgraph = dqm_app.modulegraph
        dqm_mgraph.add_endpoint(fragment_connection_name, "trb_dqm.data_fragment_all", Direction.IN, toposort=True)            
        dqm_mgraph.add_endpoint(request_connection_name, f"trb_dqm.request_output_{app_name}", Direction.OUT)

        # Add the new geoid-to-connections map to the
        # TriggerRecordBuilder.
        old_trb_conf = dqm_mgraph.get_module("trb_dqm").conf
        new_trb_map = old_trb_conf.map + trb_geoid_to_connection
        dqm_mgraph.reset_module_conf("trb_dqm", trb.ConfParams(general_queue_timeout=old_trb_conf.general_queue_timeout,
                                                          reply_connection_name = fragment_connection_name,
                                                          max_time_window = old_trb_conf.max_time_window,
                                                          trigger_record_timeout_ms = old_trb_conf.trigger_record_timeout_ms,
                                                          map=trb.mapgeoidconnections(new_trb_map)))

def connect_all_fragment_producers(the_system, dataflow_name="dataflow", verbose=False):
    """
    Connect all fragment producers in the system to the appropriate
    queues in the dataflow app.
    """
    for name, app in the_system.apps.items():
        if name==dataflow_name:
            continue
        connect_fragment_producers(name, the_system, verbose)
