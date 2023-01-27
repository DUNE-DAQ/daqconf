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

from daqconf.core.conf_utils import Direction
from daqconf.core.sourceid import source_id_raw_str, ensure_subsystem_string

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
        if producer.is_mlt_producer:
            source_id = producer.source_id
            mlt_links.append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )
    if verbose:
        console.log(f"Adding {len(mlt_links)} links to mlt.links: {mlt_links}")
    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mgraph.reset_module_conf("mlt", mlt.ConfParams(links=mlt_links, 
                                                   dfo_connection=old_mlt_conf.dfo_connection, 
                                                   dfo_busy_connection=old_mlt_conf.dfo_busy_connection,
                                                   hsi_trigger_type_passthrough=old_mlt_conf.hsi_trigger_type_passthrough,
						   buffer_timeout=old_mlt_conf.buffer_timeout,
                                                   td_out_of_timeout=old_mlt_conf.td_out_of_timeout,
                                                   td_readout_limit=old_mlt_conf.td_readout_limit,
                                                   ignore_tc=old_mlt_conf.ignore_tc,
                                                   td_readout_map=old_mlt_conf.td_readout_map))

def remove_mlt_link(the_system, source_id, mlt_app_name="trigger"):
    """
    Remove the given source_id (which should be a dict with keys "system", "region", "element") from the list of links to request data from in the MLT.
    """
    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mlt_links = old_mlt_conf.links
    if source_id not in mlt_links:
        raise ValueError(f"SourceID {source_id} not in MLT links list")
    mlt_links.remove(source_id)
    mgraph.reset_module_conf("mlt", mlt.ConfParams(links=mlt_links, 
                                                   dfo_connection=old_mlt_conf.dfo_connection, 
                                                   dfo_busy_connection=old_mlt_conf.dfo_busy_connection,
                                                   hsi_trigger_type_passthrough=old_mlt_conf.hsi_trigger_type_passthrough,
                                                   buffer_timeout=old_mlt_conf.buffer_timeout,
					       	   td_out_of_timeout=old_mlt_conf.td_out_of_timeout,
                                                   td_readout_limit=old_mlt_conf.td_readout_limit,
                                                   ignore_tc=old_mlt_conf.ignore_tc,
                                                   td_readout_map=old_mlt_conf.td_readout_map))
 
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
        return []
    
    # Create fragment sender. We can do this before looping over the
    # producers because it doesn't need any settings from them
#    app.modulegraph.add_module("fragment_sender",
#                               plugin = "FragmentSender",
#                               conf = None)

    # For each producer, we:
    # 1. Add it to the SourceID -> queue name map that is used in RequestReceiver
    # 2. Connect the relevant RequestReceiver output queue to the request input queue of the fragment producer
    # 3. Connect the fragment output queue of the producer module to the FragmentSender

    request_connection_name = f"data_requests_for_{app_name}"

    
    source_id_to_queue_inst = []
    trb_source_id_to_connection = []

    for producer in producers.values():
        source_id = producer.source_id
        queue_inst = f"data_request_q_for_{source_id_raw_str(producer.source_id)}"
        source_id_to_queue_inst.append(rrcv.sourceidinst(source_id = source_id.id,
                                                  system  = ensure_subsystem_string(source_id.subsystem),
                                                  connection_uid = queue_inst))
        trb_source_id_to_connection.append(trb.sourceidinst(source_id = source_id.id,
                                                     system  = ensure_subsystem_string(source_id.subsystem),
                                                     connection_uid = request_connection_name))
        
        # Connect the fragment output queue to the fragment sender
#        app.modulegraph.connect_modules(producer.fragments_out, "fragment_sender.input_queue")
        
    # Create request receiver

    if verbose:
        console.log(f"Creating request_receiver for {app_name} with source_id_to_queue_inst: {source_id_to_queue_inst}")
    app.modulegraph.add_module("request_receiver",
                               plugin = "RequestReceiver",
                               conf = rrcv.ConfParams(map = source_id_to_queue_inst ))
    
    for producer in producers.values():
        # It looks like RequestReceiver wants its endpoint names to
        # start "data_request_" for the purposes of checking the queue
        # type, but doesn't care what the queue instance name is (as
        # long as it matches what's in the map above), so we just set
        # the endpoint name and queue instance name to the same thing
        queue_inst = f"data_request_q_for_{source_id_raw_str(producer.source_id)}"
        app.modulegraph.connect_modules(f"request_receiver.data_request_{source_id_raw_str(producer.source_id)}", producer.requests_in, queue_inst)

    # Connect request receiver to TRB output in DF app
    app.modulegraph.add_endpoint(request_connection_name,
                                 internal_name = "request_receiver.input", 
                                 inout = Direction.IN)
                               
    trb_apps = [ (name,app) for (name,app) in the_system.apps.items() if "TriggerRecordBuilder" in [n.plugin for n in app.modulegraph.module_list()] ]
        
    for trb_app_name, trb_app_conf in trb_apps:
        fragment_connection_name = f"fragments_to_{trb_app_name}"
        app.modulegraph.add_endpoint(fragment_connection_name, None, Direction.OUT)
        df_mgraph = trb_app_conf.modulegraph
        trb_module_name = [n.name for n in df_mgraph.module_list() if n.plugin == "TriggerRecordBuilder"][0]
        df_mgraph.add_endpoint(fragment_connection_name, f"{trb_module_name}.data_fragment_all", Direction.IN, toposort=True)            
        df_mgraph.add_endpoint(request_connection_name, f"{trb_module_name}.request_output_{app_name}", Direction.OUT)

    return trb_source_id_to_connection
                          

def connect_all_fragment_producers(the_system, dataflow_name="dataflow", verbose=False):
    """
    Connect all fragment producers in the system to the appropriate
    queues in the dataflow app.
    """
    trb_source_id_map = []
    for name, app in the_system.apps.items():
        if name==dataflow_name:
            continue
        trb_source_id_map += connect_fragment_producers(name, the_system, verbose)
        
    trb_apps = [ (name,app) for (name,app) in the_system.apps.items() if "TriggerRecordBuilder" in [n.plugin for n in app.modulegraph.module_list()] ]
    
    for trb_app_name, trb_app_conf in trb_apps:
        fragment_connection_name = f"fragments_to_{trb_app_name}"
        df_mgraph = trb_app_conf.modulegraph
        trb_module_name = [n.name for n in df_mgraph.module_list() if n.plugin == "TriggerRecordBuilder"][0]

        # Add the new source_id-to-connections map to the
        # TriggerRecordBuilder.
        old_trb_conf = df_mgraph.get_module(trb_module_name).conf
        new_trb_map = old_trb_conf.map + trb_source_id_map
        df_mgraph.reset_module_conf(trb_module_name, trb.ConfParams(general_queue_timeout=old_trb_conf.general_queue_timeout,
                                                               source_id = old_trb_conf.source_id,
                                                          reply_connection_name = fragment_connection_name,
                                                          max_time_window = old_trb_conf.max_time_window,
                                                          trigger_record_timeout_ms = old_trb_conf.trigger_record_timeout_ms,
                                                          map=trb.mapsourceidconnections(new_trb_map)))
