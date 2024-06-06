# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

import moo.otypes

moo.otypes.load_types('trigger/moduleleveltrigger.jsonnet')
moo.otypes.load_types('dfmodules/triggerrecordbuilder.jsonnet')

import dunedaq.trigger.moduleleveltrigger as mlt
import dunedaq.dfmodules.triggerrecordbuilder as trb

from daqconf.core.conf_utils import Direction
from daqconf.core.sourceid import source_id_raw_str, ensure_subsystem_string
from daqconf.core.sourceid import TAInfo, TPInfo, TCInfo
from daqdataformats import SourceID
from .console import console

def set_mlt_links(the_system, trg_infos, mlt_app_name="trigger", verbose=False):
    """
    The MLT needs to know the full list of fragment producers in the
    system so it can populate the TriggerDecisions it creates. This
    function gets all the fragment producers in the system and adds their
    GeoIDs to the MLT's config. It assumes that the ModuleLevelTrigger
    lives in an application with name `mlt_app_name` and has the name
    "mlt".
    """

    a_group = 0
    mlt_readout_map = {
        0: {
            'elements':
            {
                'Trigger': [],
                'Detector_Readout': []
            }
        }
    }
    ### additional mapping to allow ROI readout
    for trigger_sid,conf in trg_infos.items():

        if isinstance(conf, TAInfo):
            # for key in mlt_readout_map.keys():
                # if mlt_readout_map[key]["group"] == conf.region_id:
                    # mlt_readout_map[key]["elements"]["Trigger"].append(trigger_sid)
            mlt_readout_map[a_group]["elements"]["Trigger"].append(trigger_sid)

        elif isinstance(conf, TPInfo):
            # for key in mlt_readout_map.keys():
            #     if key == conf.tp_ru_sid:
            #         mlt_readout_map[key]["group"] = conf.region_id
            #         mlt_readout_map[key]["elements"]["Trigger"].append(conf.tp_ru_sid)
            #         mlt_readout_map[key]["elements"]["Trigger"].append(trigger_sid)
            mlt_readout_map[a_group]["elements"]["Trigger"].append(conf.tp_ru_sid)
            mlt_readout_map[a_group]["elements"]["Trigger"].append(trigger_sid)
            
        elif isinstance(conf, TCInfo):
            # mlt_map_entry = { "group": -1, "elements": {"Trigger": [trigger_sid] } }
            # mlt_readout_map[-1] = mlt_map_entry
            mlt_readout_map[a_group]["elements"]["Trigger"].append(trigger_sid)
        else:
            # readout unit
            # mlt_map_entry = { "group": trigger_sid, "elements": { "Trigger": [], "Detector_Readout": [] } }
            for stream in conf.ru_desc.streams:
                mlt_readout_map[a_group]["elements"]["Detector_Readout"].append(stream.src_id)
            # mlt_readout_map[trigger_sid] = mlt_map_entry

    if verbose:
        console.log(f"MLT Readout Map: {mlt_readout_map}")

    mlt_links = {"mandatory": [], "groups": []}
    for key in mlt_readout_map.keys():
        if key != -1:
            mlt_links["groups"].append({"group": key, "links": []})
    
    for producer in the_system.get_fragment_producers():
        if producer.is_mlt_producer:
            source_id = producer.source_id
            # case for HSI
            if source_id.subsystem == SourceID.Subsystem.kHwSignalsInterface:
                mlt_links["mandatory"].append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )
            # case for RU
            elif source_id.subsystem == SourceID.Subsystem.kDetectorReadout:
                matched = False
                for key in mlt_readout_map.keys():
                    if key != -1:
                        if source_id.id in mlt_readout_map[key]["elements"]["Detector_Readout"]:
                            mlt_links["groups"][key]["links"].append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )
                            matched = True
                # special case to cover readout that is not a TP source for trigger
                if not matched:
                    mlt_links["groups"].append({"group": len(mlt_links["groups"]), "links": []})
                    mlt_links["groups"][len(mlt_links["groups"])-1]["links"].append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )
            # anything else (TP, TA, TC buffers)
            else:
                for key in mlt_readout_map.keys():
                    if source_id.id in mlt_readout_map[key]["elements"]["Trigger"]:
                        match key:
                            case -1:
                                mlt_links["mandatory"].append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )
                            case _:
                                mlt_links["groups"][key]["links"].append( mlt.SourceID(subsystem=ensure_subsystem_string(source_id.subsystem), element=source_id.id) )

    if verbose:
        tot = 0
        for group in mlt_links["groups"]:
            tot += len(group["links"])
        tot += len(mlt_links["mandatory"])
        console.log(f"Adding {tot} links to mlt.links")

    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mgraph.reset_module_conf("mlt", mlt.ConfParams(mandatory_links=mlt_links["mandatory"],
                                                   groups_links=mlt_links["groups"],
                                                   merge_overlapping_tcs=old_mlt_conf.merge_overlapping_tcs,
						   buffer_timeout=old_mlt_conf.buffer_timeout,
                                                   td_out_of_timeout=old_mlt_conf.td_out_of_timeout,
                                                   td_readout_limit=old_mlt_conf.td_readout_limit,
                                                   ignore_tc=old_mlt_conf.ignore_tc,
                                                   use_readout_map=old_mlt_conf.use_readout_map,
                                                   td_readout_map=old_mlt_conf.td_readout_map,
                                                   use_roi_readout=old_mlt_conf.use_roi_readout,
                                                   roi_conf=old_mlt_conf.roi_conf,
                                                   use_bitwords=old_mlt_conf.use_bitwords,
                                                   trigger_bitwords=old_mlt_conf.trigger_bitwords,
                                                   enable_latency_monit=old_mlt_conf.enable_latency_monit,
                                                   use_latency_offset=old_mlt_conf.use_latency_offset))

def remove_mlt_link(the_system, source_id, mlt_app_name="trigger"):
    """
    Remove the given source_id (which should be a dict with keys "system", "region", "element") from the list of links to request data from in the MLT.
    """
    mgraph = the_system.apps[mlt_app_name].modulegraph
    old_mlt_conf = mgraph.get_module("mlt").conf
    mlt_mandatory_links = old_mlt_conf.mandatory_links
    mlt_groups_links = old_mlt_conf.groups_links
    if source_id not in mlt_mandatory_links and source_id not in mlt_groups_links:
        raise ValueError(f"SourceID {source_id} not in MLT links list")
    if source_id in mlt_mandatory_links:
        mlt_mandatory_links.remove(source_id)
    if source_id in mlt_groups_links:
        mlt_groups_links.remove(source_id)
    mgraph.reset_module_conf("mlt", mlt.ConfParams(mandatory_links=mlt_mandatory_links,
                                                   groups_links=mlt_groups_links,
                                                   merge_overlapping_tcs=old_mlt_conf.merge_overlapping_tcs,
                                                   buffer_timeout=old_mlt_conf.buffer_timeout,
                                                   td_out_of_timeout=old_mlt_conf.td_out_of_timeout,
                                                   td_readout_limit=old_mlt_conf.td_readout_limit,
                                                   ignore_tc=old_mlt_conf.ignore_tc,
                                                   use_readout_map=old_mlt_conf.use_readout_map,
                                                   td_readout_map=old_mlt_conf.td_readout_map,
                                                   use_roi_readout=old_mlt_conf.use_roi_readout,
                                                   roi_conf=old_mlt_conf.roi_conf,
                                                   use_bitwords=old_mlt_conf.use_bitwords,
                                                   trigger_bitwords=old_mlt_conf.trigger_bitwords,
                                                   enable_latency_monit=old_mlt_conf.enable_latency_monit,
                                                   use_latency_offset=old_mlt_conf.use_latency_offset))

def create_direct_producer_connections(app_name, the_system, verbose=False):
    app = the_system.apps[app_name]
    producers = app.modulegraph.fragment_producers
    if len(producers) == 0:
        return
    if verbose:
        console.log(f"Connecting fragment producers in {app_name} directly to TRBs")

    for producer in producers.values():
        queue_inst = f"data_requests_for_{source_id_raw_str(producer.source_id)}"
        # Connect request receiver to TRB output in DF app
        app.modulegraph.add_endpoint(queue_inst,
                                 internal_name = producer.requests_in, 
                                 data_type = "DataRequest",
                                 inout = Direction.IN)

    trb_apps = [ (name,app) for (name,app) in the_system.apps.items() if "TriggerRecordBuilder" in [n.plugin for n in app.modulegraph.module_list()] ]

    for trb_app_name, trb_app_conf in trb_apps:
        fragment_connection_name = f"fragments_to_{trb_app_name}"
        app.modulegraph.add_endpoint(fragment_connection_name, None, "Fragment", Direction.OUT)
        df_mgraph = trb_app_conf.modulegraph
        trb_module_name = [n.name for n in df_mgraph.module_list() if n.plugin == "TriggerRecordBuilder"][0]
        for producer in producers.values():
            queue_inst = f"data_requests_for_{source_id_raw_str(producer.source_id)}"
            df_mgraph.add_endpoint(queue_inst, f"{trb_module_name}.request_output_{source_id_raw_str(producer.source_id)}", "DataRequest", Direction.OUT)


def create_producer_connections_with_aggregation(app_name, the_system, verbose=False):
    app = the_system.apps[app_name]
    producers = app.modulegraph.fragment_producers
    if len(producers) == 0:
        return
    if verbose:
        console.log(f"Connecting fragment producers in {app_name} to TRBs using a FragmentAggregator")

    # Create the fragment aggregator. 
    app.modulegraph.add_module(f"fragment_aggregator_{app_name}",
                               plugin = "FragmentAggregator",
                               conf = None)

    # Declare the fragment aggregator endpoint that receives DataRequests
    queue_inst = f"data_requests_for_{app_name}"
    app.modulegraph.add_endpoint(queue_inst,
                                 internal_name = f"fragment_aggregator_{app_name}.data_req_input",
                                 data_type = "DataRequest",
                                 inout = Direction.IN)

    # Connect the DLH Fragment output queues to the fragment aggregator
    for producer in producers.values():
        app.modulegraph.connect_modules(producer.fragments_out, f"fragment_aggregator_{app_name}.fragment_input", "Fragment", queue_name="fragment_queue", size_hint=100000)

    # Connect the DLH DataRequest input queues to the fragment aggregator
    for producer in producers.values():
        app.modulegraph.connect_modules(f"fragment_aggregator_{app_name}.request_output_{source_id_raw_str(producer.source_id)}", producer.requests_in, "DataRequest", queue_name=f"data_requests_for_{source_id_raw_str(producer.source_id)}", size_hint=1000)

    trb_apps = [ (name,app) for (name,app) in the_system.apps.items() if "TriggerRecordBuilder" in [n.plugin for n in app.modulegraph.module_list()] ]

    # Declare the fragment aggregator endpoints that send Fragments
    for trb_app_name, trb_app_conf in trb_apps:
        fragment_connection_name = f"fragments_to_{trb_app_name}"
        app.modulegraph.add_endpoint(fragment_connection_name, None, "Fragment", Direction.OUT)
        df_mgraph = trb_app_conf.modulegraph
        trb_module_name = [n.name for n in df_mgraph.module_list() if n.plugin == "TriggerRecordBuilder"][0]
        queue_inst = f"data_requests_for_{app_name}"
        for producer in producers.values():
            df_mgraph.add_endpoint(queue_inst, f"{trb_module_name}.request_output_{source_id_raw_str(producer.source_id)}", "DataRequest", Direction.OUT)


def connect_fragment_producers(app_name, the_system, verbose=False):
    """Connect the data request and fragment sending queues from all of
       the fragment producers in the app with name `app_name` to the
       appropriate endpoints of the dataflow app."""

    app = the_system.apps[app_name]
    producers = app.modulegraph.fragment_producers

    # Nothing to do if there are no fragment producers. Return now so we don't create unneeded modules or connections
    if len(producers) == 0:
        return

    dro_producer = False
    for producer in producers.values():
        if producer.source_id.subsystem == SourceID.Subsystem.kDetectorReadout:
            dro_producer = True

    if dro_producer:
        create_producer_connections_with_aggregation(app_name, the_system, verbose)
    else:
        create_direct_producer_connections(app_name, the_system, verbose)


def connect_all_fragment_producers(the_system, dataflow_name="dataflow", verbose=False):
    """
    Connect all fragment producers in the system to the appropriate
    queues in the dataflow app.
    """
    for name, app in the_system.apps.items():
        if name==dataflow_name:
            continue
        connect_fragment_producers(name, the_system, verbose)
        
    trb_apps = [ (name,app) for (name,app) in the_system.apps.items() if "TriggerRecordBuilder" in [n.plugin for n in app.modulegraph.module_list()] ]
    
    for trb_app_name, trb_app_conf in trb_apps:
        fragment_connection_name = f"fragments_to_{trb_app_name}"
        df_mgraph = trb_app_conf.modulegraph
        trb_module_name = [n.name for n in df_mgraph.module_list() if n.plugin == "TriggerRecordBuilder"][0]
        df_mgraph.add_endpoint(fragment_connection_name, f"{trb_module_name}.data_fragment_all", "Fragment", Direction.IN, toposort=True)

        # Add the new source_id-to-connections map to the
        # TriggerRecordBuilder.
        old_trb_conf = df_mgraph.get_module(trb_module_name).conf
        df_mgraph.reset_module_conf(trb_module_name, trb.ConfParams(general_queue_timeout=old_trb_conf.general_queue_timeout,
                                                               source_id = old_trb_conf.source_id,
                                                          max_time_window = old_trb_conf.max_time_window,
                                                          trigger_record_timeout_ms = old_trb_conf.trigger_record_timeout_ms))
