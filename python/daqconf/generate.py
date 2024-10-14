from gc import disable
from daqconf.assets import resolve_asset_file
from daqconf.utils import find_oksincludes
import conffwk
import glob
import os

from distutils.command import install_egg_info


def generate_dataflow(
    oksfile,
    include,
    n_dfapps,
    tpwriting_enabled,
    generate_segment,
    n_data_writers=1,
):
    """Simple script to create an OKS configuration file for a dataflow segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify. Any necessary objects not supplied
    by included files will be generated and saved in the output file.

    """

    includefiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
    ]

    res, extra_includes = find_oksincludes(include, os.path.dirname(oksfile))
    if res:
        includefiles += extra_includes
    else:
        return

    dal = conffwk.dal.module("generated", includefiles)
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)
    db.set_active(oksfile)

    hosts = []
    for vhost in db.get_dals(class_name="VirtualHost"):
        hosts.append(vhost.id)
        if vhost.id == "vlocalhost":
            host = vhost
    if "vlocalhost" not in hosts:
        cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
        db.update_dal(cpus)
        phdal = dal.PhysicalHost("localhost", contains=[cpus])
        db.update_dal(phdal)
        host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
        db.update_dal(host)
        hosts.append("vlocalhost")

    # Services
    dfo_control = db.get_dal(class_name="Service", uid="dfo-01_control")
    tpw_control = db.get_dal(class_name="Service", uid="tp-stream-writer_control")

    # Source IDs
    tpw_source_id = db.get_dal("SourceIDConf", uid="srcid-tp-stream-writer")

    # Queue Rules
    trigger_record_q_rule = db.get_dal(
        class_name="QueueConnectionRule", uid="trigger-record-q-rule"
    )
    dfapp_qrules = [trigger_record_q_rule]

    # Net Rules
    frag_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="frag-net-rule")
    df_token_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="df-token-net-rule"
    )
    tpset_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="tpset-net-rule"
    )
    ti_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="ti-net-rule")
    td_dfo_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="td-dfo-net-rule"
    )
    td_trb_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="td-trb-net-rule"
    )
    data_req_trig_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-trig-net-rule"
    )
    data_req_hsi_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-hsi-net-rule"
    )
    data_req_readout_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-readout-net-rule"
    )
    dfapp_netrules = [
        td_trb_net_rule,
        frag_net_rule,
        df_token_net_rule,
        data_req_hsi_net_rule,
        data_req_readout_net_rule,
        data_req_trig_net_rule,
    ]
    dfo_netrules = [td_dfo_net_rule, ti_net_rule, df_token_net_rule]
    tpw_netrules = [tpset_net_rule]

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")

    dfo_conf = db.get_dal(class_name="DFOConf", uid="dfoconf-01")
    dfo = dal.DFOApplication(
        "dfo-01",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[dfo_control],
        network_rules=dfo_netrules,
        opmon_conf=opmon_conf,
        dfo=dfo_conf,
    )
    db.update_dal(dfo)

    trb_conf = db.get_dal(class_name="TRBConf", uid="trb-01")
    dw_conf = db.get_dal(class_name="DataWriterConf", uid="dw-01")
    dfhw = db.get_dal(class_name="DFHWConf", uid="dfhw-01")
    dfapps = []
    for dfapp_idx in range(n_dfapps):
        dfapp_id = dfapp_idx + 1

        # Offset sids by one so that TPW sourceID can stay at 1
        dfapp_source_id = dal.SourceIDConf(
            f"srcid-df-{dfapp_id:02}", sid=dfapp_id + 1, subsystem="TR_Builder"
        )
        db.update_dal(dfapp_source_id)

        dfapp_control = dal.Service(
            f"df-{dfapp_id:02}_control", protocol="rest", port=dfo_control.port+1 + dfapp_id
        )
        db.update_dal(dfapp_control)

        dfapp = dal.DFApplication(
            f"df-{dfapp_id:02}",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[dfapp_control],
            source_id=dfapp_source_id,
            queue_rules=dfapp_qrules,
            network_rules=dfapp_netrules,
            opmon_conf=opmon_conf,
            trb=trb_conf,
            data_writers=[dw_conf] * n_data_writers,
            uses=dfhw,
        )
        db.update_dal(dfapp)
        dfapps.append(dfapp)

    tpwapps = []
    if tpwriting_enabled:
        tpw_writer_conf = db.get_dal(
            class_name="TPStreamWriterConf", uid="tp-stream-writer-conf"
        )

        tpwapp = dal.TPStreamWriterApplication(
            "tp-stream-writer",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[tpw_control],
            source_id=tpw_source_id,
            network_rules=tpw_netrules,
            opmon_conf=opmon_conf,
            tp_writer=tpw_writer_conf,
        )
        db.update_dal(tpwapp)
        tpwapps.append(tpwapp)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller_service = dal.Service(
            "df-controller_control", protocol="grpc", port=5600
        )
        db.update_dal(controller_service)
        controller = dal.RCApplication(
            "df-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[controller_service],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"df-segment", controller=controller, applications=[dfo] + dfapps + tpwapps
        )
        db.update_dal(seg)

    db.commit()
    return


def generate_hsi(
    oksfile,
    include,
    generate_segment,
):
    """Simple script to create an OKS configuration file for a FakeHSI segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify. Any necessary objects not supplied
    by included files will be generated and saved in the output file.


    """

    includefiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
        "schema/appmodel/trigger.schema.xml",
    ]

    res, extra_includes = find_oksincludes(include, os.path.dirname(oksfile))
    if res:
        includefiles += extra_includes
    else:
        return

    dal = conffwk.dal.module("generated", includefiles)
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)
    db.set_active(oksfile)

    hosts = []
    for vhost in db.get_dals(class_name="VirtualHost"):
        hosts.append(vhost.id)
        if vhost.id == "vlocalhost":
            host = vhost
    if "vlocalhost" not in hosts:
        cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
        db.update_dal(cpus)
        phdal = dal.PhysicalHost("localhost", contains=[cpus])
        db.update_dal(phdal)
        host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
        db.update_dal(host)
        hosts.append("vlocalhost")

    # Services
    hsi_control = db.get_dal(class_name="Service", uid="hsi-01_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
    tc_app_control = db.get_dal(class_name="Service", uid="hsi-to-tc-app_control")
    hsievents = db.get_dal(class_name="Service", uid="HSIEvents")

    # Source IDs
    hsi_source_id = db.get_dal(class_name="SourceIDConf", uid="hsi-srcid-01")
    hsi_tc_source_id = db.get_dal(class_name="SourceIDConf", uid="hsi-tc-srcid-1")

    # Queue Rules
    hsi_dlh_queue_rule = db.get_dal(
        class_name="QueueConnectionRule", uid="hsi-dlh-data-requests-queue-rule"
    )
    hsi_qrules = [hsi_dlh_queue_rule]

    # Net Rules
    tc_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="tc-net-rule")
    hsi_rule = db.get_dal(class_name="NetworkConnectionRule", uid="hsi-rule")
    ts_hsi_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="ts-hsi-net-rule"
    )
    data_req_hsi_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-hsi-net-rule"
    )
    hsi_netrules = [hsi_rule, data_req_hsi_net_rule, ts_hsi_net_rule]
    tc_netrules = [hsi_rule, tc_net_rule]

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")
    hsi_handler = db.get_dal(class_name="DataHandlerConf", uid="def-hsi-handler")
    fakehsi = db.get_dal(class_name="FakeHSIEventGeneratorConf", uid="fakehsi")

    hsi = dal.FakeHSIApplication(
        "hsi-01",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[hsi_control],
        source_id=hsi_source_id,
        queue_rules=hsi_qrules,
        network_rules=hsi_netrules,
        opmon_conf=opmon_conf,
        link_handler=hsi_handler,
        generator=fakehsi,
    )
    db.update_dal(hsi)

    hsi_to_tc_conf = db.get_dal(class_name="HSI2TCTranslatorConf", uid="hsi-to-tc-conf")

    hsi_to_tc = dal.HSIEventToTCApplication(
        "hsi-to-tc-app",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[dataRequests, hsievents, tc_app_control],
        source_id=hsi_tc_source_id,
        network_rules=tc_netrules,
        opmon_conf=opmon_conf,
        hsevent_to_tc_conf=hsi_to_tc_conf,
    )
    db.update_dal(hsi_to_tc)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller_service = dal.Service(
            "hsi-controller_control", protocol="grpc", port=5800
        )
        db.update_dal(controller_service)
        controller = dal.RCApplication(
            "hsi-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[controller_service],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"hsi-segment", controller=controller, applications=[hsi, hsi_to_tc]
        )
        db.update_dal(seg)

    db.commit()
    return


def generate_readout(
    readoutmap,
    oksfile,
    include,
    generate_segment,
    emulated_file_name="asset://?checksum=e96fd6efd3f98a9a3bfaba32975b476e",
    tpg_enabled=True,
    hosts_to_use=[],
):
    """Simple script to create an OKS configuration file for all
  ReadoutApplications defined in a readout map.

    The file will automatically include the relevant schema files and
  any other OKS files you specify. Any necessary objects not supplied
  by included files will be generated and saved in the output file.

   Example:
     generate_readoutOKS -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs \
       config/np04readoutmap.data.xml readoutApps.data.xml

   Will load hosts, connections and moduleconfs data files as well as
  the readoutmap (config/np04readoutmap.data.xml) and write the
  generated apps to readoutApps.data.xml.

     generate_readoutOKS --session --segment \
       -i appmodel/fsm -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs  \
       config/np04readoutmap.data.xml np04readout-session.data.xml

   Will do the same but in addition it will generate a containing
  Segment for the apps and a containing Session for the Segment.

  NB: Currently FSM generation is not implemented so you must include
  an fsm file in order to generate a Segment

  """

    if not readoutmap.endswith(".data.xml"):
        readoutmap = readoutmap + ".data.xml"

    print(f"Readout map file {readoutmap}")

    includefiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
        "schema/appmodel/trigger.schema.xml",
        "schema/appmodel/fdmodules.schema.xml",
        "schema/appmodel/wiec.schema.xml",
        readoutmap,
    ]

    searchdirs = [path for path in os.environ["DUNEDAQ_DB_PATH"].split(":")]
    searchdirs.append(os.path.dirname(oksfile))
    for inc in include:
        # print (f"Searching for {inc}")
        match = False
        inc = inc.removesuffix(".xml")
        if inc.endswith(".data"):
            sub_dirs = ["config", "data"]
        elif inc.endswith(".schema"):
            sub_dirs = ["schema"]
        else:
            sub_dirs = ["*"]
            inc = inc + "*"
        for path in searchdirs:
            # print (f"   {path}/{inc}.xml")
            matches = glob.glob(f"{inc}.xml", root_dir=path)
            if len(matches) == 0:
                for search_dir in sub_dirs:
                    # print (f"   {path}/{search_dir}/{inc}.xml")
                    matches = glob.glob(f"{search_dir}/{inc}.xml", root_dir=path)
                    for filename in matches:
                        if filename not in includefiles:
                            print(f"Adding {filename} to include list")
                            includefiles.append(filename)
                        else:
                            print(f"{filename} already in include list")
                        match = True
                        break
                    if match:
                        break
                if match:
                    break
            else:
                for filename in matches:
                    if filename not in includefiles:
                        print(f"Adding {filename} to include list")
                        includefiles.append(filename)
                    else:
                        print(f"{filename} already in include list")
                    match = True
                    break

        if not match:
            print(f"Error could not find include file for {inc}")
            return

    dal = conffwk.dal.module("generated", includefiles)
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)
    db.set_active(oksfile)

    detector_connections = db.get_dals(class_name="DetectorToDaqConnection")

    # Check tpg_enabled here, if it is False, then we want to make our own RawDataProcessor
    if len(db.get_dals(class_name="LatencyBuffer")) > 0:
        print(f"Using predefined Latency buffers etc.")
        reqhandler = db.get_dal(
            class_name="RequestHandler", uid="def-data-request-handler"
        )
        latencybuffer = db.get_dal(class_name="LatencyBuffer", uid="def-latency-buf")
        linkhandler = db.get_dal(class_name="DataHandlerConf", uid="def-link-handler")
        tphandler = db.get_dal(class_name="DataHandlerConf", uid="def-tp-handler")

    else:
        print(f"Creating locally defined Latency buffers etc.")
        reqhandler = dal.RequestHandler("rh-1")
        db.update_dal(reqhandler)
        latencybuffer = dal.LatencyBuffer(
            "lb-1-gen",
            numa_aware=True,
            numa_node=1,
            size=139008,
            alignment_size=4096,
            intrinsic_allocator=True,
        )
        db.update_dal(latencybuffer)

        pedsub = dal.AVXFrugalPedestalSubtractProcessor(
            "tpg-pedsub-proc-gen", accum_limit=10
        )
        db.update_dal(pedsub)
        thresh = dal.AVXThresholdProcessor(
            "tpg-threshold-proc-gen", plane0=100, plane1=100, plane2=100
        )
        db.update_dal(thresh)

        dataproc = dal.RawDataProcessor(
            "dataproc-1-gen",
            channel_map="PD2HDChannelMap",
            processing_steps=[pedsub, thresh],
        )

        db.update_dal(dataproc)
        linkhandler = dal.DataHandlerConf(
            "linkhandler-1-gen",
            template_for="FDDataHandlerModule",
            input_data_type="WIBEthFrame",
            request_handler=reqhandler,
            latency_buffer=latencybuffer,
            data_processor=dataproc,
        )
        db.update_dal(linkhandler)
        tphandler = dal.DataHandlerConf(
            "tphandler-1-gen",
            template_for="TriggerDataHandlerModule",
            input_data_type="TriggerPrimitive",
            request_handler=reqhandler,
            latency_buffer=latencybuffer,
            data_processor=dataproc,
        )
        db.update_dal(tphandler)
    try:
        rule = db.get_dal(
            class_name="NetworkConnectionRule", uid="data-req-readout-net-rule"
        )
    except:
        # Failed to get rule, now we have to invent some
        netrules = generate_net_rules(dal, db)
    else:
        netrules = [rule]
        # Assume we have all the other rules we need
        for rule in ["tpset-net-rule", "ts-net-rule", "ta-net-rule"]:
            netrules.append(db.get_dal(class_name="NetworkConnectionRule", uid=rule))

    try:
        rule = db.get_dal(
            class_name="QueueConnectionRule", uid="fd-dlh-data-requests-queue-rule"
        )
    except:
        qrules = generate_queue_rules(dal, db)
    else:
        qrules = [rule]
        for rule in ["fa-queue-rule", "wib-eth-raw-data-rule", "tp-queue-rule"]:
            qrules.append(db.get_dal(class_name="QueueConnectionRule", uid=rule))

    hosts = []
    if len(hosts_to_use) == 0:
        for vhost in db.get_dals(class_name="VirtualHost"):
            if vhost.id == "vlocalhost":
                hosts.append(vhost.id)
        if "vlocalhost" not in hosts:
            cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
            db.update_dal(cpus)
            phdal = dal.PhysicalHost("localhost", contains=[cpus])
            db.update_dal(phdal)
            host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
            db.update_dal(host)
            hosts.append("vlocalhost")
    else:
        for vhost in db.get_dals(class_name="VirtualHost"):
            if vhost.id in hosts_to_use:
                hosts.append(vhost.id)
    assert len(hosts) > 0

    rohw = dal.RoHwConfig(f"rohw-{detector_connections[0].id}")
    db.update_dal(rohw)

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")

    appnum = 0
    nicrec = None
    flxcard = None
    wm_conf = None
    hermes_conf = None
    ruapps = []
    for connection in detector_connections:
        hostnum = appnum % len(hosts)
        # print(f"Looking up host[{hostnum}] ({hosts[hostnum]})")
        host = db.get_dal(class_name="VirtualHost", uid=hosts[hostnum])

        # Find which type of DataReceiver we need for this connection
        for resource in connection.contains:
            if "DetDataReceiver" in resource.oksTypes():
                receiver = resource
                break
        # Emulated stream
        if type(receiver).__name__ == "FakeDataReceiver":
            if nicrec == None:
                try:
                    stream_emu = db.get_dal(
                        class_name="StreamEmulationParameters", uid="stream-emu"
                    )
                except:
                    stream_emu = dal.StreamEmulationParameters(
                        "stream-emu",
                        data_file_name=resolve_asset_file(emulated_file_name),
                        input_file_size_limit=1000000,
                        set_t0=True,
                        random_population_size=100000,
                        frame_error_rate_hz=0,
                        generate_periodic_adc_pattern=True,
                        TP_rate_per_channel=1,
                    )
                    db.update_dal(stream_emu)

                print("Generating fake DataReaderConf")
                nicrec = dal.DPDKReaderConf(
                    f"nicrcvr-fake-gen",
                    template_for="FDFakeReaderModule",
                    emulation_mode=1,
                    emulation_conf=stream_emu,
                )
                db.update_dal(nicrec)
            datareader = nicrec
        elif type(receiver).__name__ == "DPDKReceiver":
            if nicrec == None:
                print("Generating DPDKReaderConf")
                nicrec = dal.DPDKReaderConf(
                    f"nicrcvr-dpdk-gen", template_for="DPDKReaderModule"
                )
                db.update_dal(nicrec)
            if wm_conf == None:
                try:
                    wm_conf = db.get_dal("WIBModuleConf", "def-wib-conf")
                except:
                    wm_conf = generate_wibmoduleconf(dal, db)
            if hermes_conf == None:
                try:
                    hermes_conf = db.get_dal("HermesModuleConf", "def-hermes-conf")
                except:
                    hermes_conf = generate_hermesmoduleconf(dal, db)

            datareader = nicrec
            wiec_control = dal.Service(
                f"wiec-{connection.id}_control", protocol="rest", port=5600 + appnum
            )
            db.update_dal(wiec_control)

            wiec_app = dal.WIECApplication(
                f"wiec-{connection.id}",
                application_name="daq_application",
                runs_on=host,
                contains=[connection],
                wib_module_conf=wm_conf,
                hermes_module_conf=hermes_conf,
                exposes_service=[wiec_control],
            )
            db.update_dal(wiec_app)

        elif type(receiver).__name__ == "FelixInterface":
            if flxcard == None:
                print("Generating Felix DataReaderConf")
                flxcard = dal.DataReaderConf(
                    f"flxConf-1", template_for="FelixReaderModule"
                )
                db.update_dal(flxcard)
            datareader = flxcard
        else:
            print(
                f"ReadoutGroup contains unknown interface type {type(receiver).__name__}"
            )
            continue

        db.commit()

        # Services
        dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
        timeSyncs = db.get_dal(class_name="Service", uid="timeSyncs")
        triggerActivities = db.get_dal(class_name="Service", uid="triggerActivities")
        triggerPrimitives = db.get_dal(class_name="Service", uid="triggerPrimitives")
        ru_control = dal.Service(
            f"ru-{connection.id}_control", protocol="rest", port=5501 + appnum
        )
        db.update_dal(ru_control)

        # Action Plans
        readout_start = db.get_dal(class_name="ActionPlan", uid="readout-start")
        readout_stop = db.get_dal(class_name="ActionPlan", uid="readout-stop")

        ru = dal.ReadoutApplication(
            f"ru-{connection.id}",
            application_name="daq_application",
            runs_on=host,
            contains=[connection],
            network_rules=netrules,
            queue_rules=qrules,
            link_handler=linkhandler,
            data_reader=datareader,
            opmon_conf=opmon_conf,
            tp_generation_enabled=tpg_enabled,
            ta_generation_enabled=tpg_enabled,
            uses=rohw,
            exposes_service=[ru_control, dataRequests, timeSyncs],
            action_plans=[readout_start, readout_stop],
        )
        if tpg_enabled:
            ru.tp_handler = tphandler
            tp_sources = []
            tpbaseid = (appnum * 3) + 100
            for plane in range(3):
                s_id = tpbaseid + plane
                tps_dal = dal.SourceIDConf(
                    f"tp-srcid-{s_id}", sid=s_id, subsystem="Trigger"
                )
                db.update_dal(tps_dal)
                tp_sources.append(tps_dal)
            ru.tp_source_ids = tp_sources
            ru.exposes_service += [triggerActivities, triggerPrimitives]
        appnum = appnum + 1
        print(f"{ru=}")
        db.update_dal(ru)
        db.commit()
        ruapps.append(ru)
    if appnum == 0:
        print(f"No ReadoutApplications generated\n")
        return

    db.commit()

    if generate_segment:
        # fsm = db.get_dal(class_name="FSMconfiguration", uid="fsmConf-test")
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller_service = dal.Service(
            "ru-controller_control", protocol="grpc", port=5500
        )
        db.update_dal(controller_service)
        db.commit()
        controller = dal.RCApplication(
            "ru-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[controller_service],
        )
        db.update_dal(controller)
        db.commit()

        seg = dal.Segment(f"ru-segment", controller=controller, applications=ruapps)
        db.update_dal(seg)
        db.commit()

    db.commit()
    return


def generate_net_rules(dal, db):
    print(f"Generating network rules")
    netrules = []
    dataservice = dal.Service("dataFragments-gen", port=0)
    db.update_dal(dataservice)
    tpservice = dal.Service("triggerPrimitives-gen", port=0)
    db.update_dal(tpservice)
    timeservice = dal.Service("timeSync-gen", port=0)
    db.update_dal(timeservice)

    newdescr = dal.NetworkConnectionDescriptor(
        "data-req-net-input-gen",
        uid_base="data_requests_for_",
        connection_type="kSendRecv",
        data_type="DataRequest",
        associated_service=dataservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "fa-net-rule-gen",
        endpoint_class="FragmentAggregatorModule",
        descriptor=newdescr,
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "ta-publisher-gen",
        uid_base="ta_",
        connection_type="kPubSub",
        data_type="TriggerActivity",
        associated_service=dataservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "ta-net-rule-gen", endpoint_class="DataSubscriberModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "tp-net-descr-gen",
        uid_base="trigger_primitive_data_request",
        connection_type="kPubSub",
        data_type="TPSet",
        associated_service=tpservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "tp-net-rule-gen", endpoint_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "timesync-publisher-gen",
        uid_base="time_sync_",
        connection_type="kPubSub",
        data_type="TimeSync",
        associated_service=timeservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "ts-net-rule-gen", endpoint_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)
    return netrules


def generate_queue_rules(dal, db):
    qrules = []
    newdescr = dal.QueueDescriptor(
        "dataRequest-gen",
        queue_type="kFollySPSCQueue",
        data_type="DataRequest",
        uid_base="data_reqs_for_",
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "data-requests-queue-rule-gen",
        destination_class="FDDataHandlerModule",
        descriptor=newdescr,
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "aggregatorInput-gen",
        queue_type="kFollyMPMCQueue",
        data_type="Fragment",
        uid_base="fragments_from_",
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "fa-queue-rule-gen",
        destination_class="FragmentAggregatorModule",
        descriptor=newdescr,
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "rawWIBInput-gen",
        queue_type="kFollySPSCQueue",
        data_type="WIBEthFrame",
        uid_base="raw_",
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "rawInputRule-gen", destination_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "tpInput-gen",
        queue_type="kFollyMPMCQueue",
        capacity=100000,
        data_type="TriggerPrimitive",
        uid_base="tps_",
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "tpRule-gen", destination_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    return qrules


def generate_wibmoduleconf(dal, db):
    try:
        femb_settings = db.get_dal("FEMBSettings", "def-femb-settings")
    except:
        femb_settings = dal.FEMBSettings("def-femb-settings-gen")
        db.update_dal(femb_settings)

    try:
        coldadc_settings = db.get_dal("ColdADCSettings", "def-coldadc-settings")
    except:
        coldadc_settings = dal.ColdADCSettings("def-coldadc-settings-gen")
        db.update_dal(coldadc_settings)
    try:
        wibpulser = db.get_dal("WIBPulserSettings", "def-wib-pulser-setting")
    except:
        wibpulser = dal.WIBPulserSettings("def-wib-pulser-setting-gen")
        db.update_dal(wibpulser)

    wib_settings = dal.WIBSettings(
        "def-wib-settings-gen",
        femb0=femb_settings,
        femb1=femb_settings,
        femb2=femb_settings,
        femb3=femb_settings,
        coldadc_settings=coldadc_settings,
        wib_pulser=wibpulser,
    )
    db.update_dal(wib_settings)
    wm_conf = dal.WIBModuleConf("def-wibmodule-conf-gen", settings=wib_settings)
    db.update_dal(wm_conf)
    return wm_conf


def generate_hermesmoduleconf(dal, db):
    try:
        addr_table = db.get_dal("IpbusAddressTable", "Hermes-addrtab")
    except:
        addr_table = dal.IpbusAddressTable("Hermes-addrtab-gen")
        db.update_dal(addr_table)

    hermes_conf = dal.HermesModuleConf("def-hermes-conf-gen", address_table=addr_table)
    db.update_dal(hermes_conf)
    return hermes_conf


def generate_trigger(
    oksfile,
    include,
    generate_segment,
    tpg_enabled=True,
    hsi_enabled=False,
):
    """Simple script to create an OKS configuration file for a trigger segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify. Any necessary objects not supplied
    by included files will be generated and saved in the output file.

    """

    includefiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
        "schema/appmodel/trigger.schema.xml",
    ]

    res, extra_includes = find_oksincludes(include, os.path.dirname(oksfile))
    if res:
        includefiles += extra_includes
    else:
        return

    dal = conffwk.dal.module("generated", includefiles)
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)
    db.set_active(oksfile)

    hosts = []
    for vhost in db.get_dals(class_name="VirtualHost"):
        hosts.append(vhost.id)
        if vhost.id == "vlocalhost":
            host = vhost
    if "vlocalhost" not in hosts:
        cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
        db.update_dal(cpus)
        phdal = dal.PhysicalHost("localhost", contains=[cpus])
        db.update_dal(phdal)
        host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
        db.update_dal(host)
        hosts.append("vlocalhost")

    # Services
    mlt_control = db.get_dal(class_name="Service", uid="mlt_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
    tc_maker_control = db.get_dal(class_name="Service", uid="tc-maker-1_control")
    triggerActivities = db.get_dal(class_name="Service", uid="triggerActivities")
    triggerCandidates = db.get_dal(class_name="Service", uid="triggerCandidates")
    triggerInhibits = db.get_dal(class_name="Service", uid="triggerInhibits")

    # Source IDs
    mlt_source_id = db.get_dal(class_name="SourceIDConf", uid="tc-srcid-1")
    tc_source_id = db.get_dal(class_name="SourceIDConf", uid="ta-srcid-1")

    # Queue Rules
    tc_queue_rule = db.get_dal(class_name="QueueConnectionRule", uid="tc-queue-rule")
    td_queue_rule = db.get_dal(class_name="QueueConnectionRule", uid="td-queue-rule")
    ta_queue_rule = db.get_dal(class_name="QueueConnectionRule", uid="ta-queue-rule")
    mlt_qrules = [tc_queue_rule, td_queue_rule]
    tapp_qrules = [ta_queue_rule]

    # Net Rules
    tc_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="tc-net-rule")
    ta_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="ta-net-rule")
    ts_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="ts-net-rule")
    ti_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="ti-net-rule")
    td_dfo_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="td-dfo-net-rule"
    )
    data_req_trig_net_rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-trig-net-rule"
    )
    mlt_netrules = [
        tc_net_rule,
        ti_net_rule,
        td_dfo_net_rule,
        data_req_trig_net_rule,
        ts_net_rule,
    ]
    tapp_netrules = [ta_net_rule, tc_net_rule, data_req_trig_net_rule]

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")
    tc_subscriber = db.get_dal(class_name="DataReaderConf", uid="tc-subscriber-1")
    tc_handler = db.get_dal(class_name="DataHandlerConf", uid="def-tc-handler")
    mlt_conf = db.get_dal(class_name="MLTConf", uid="def-mlt-conf")
    random_tc_generator = db.get_dal(
        class_name="RandomTCMakerConf", uid="random-tc-generator"
    )
    tc_confs = [] if hsi_enabled else [random_tc_generator]

    mlt = dal.MLTApplication(
        "mlt",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[mlt_control, triggerCandidates, triggerInhibits, dataRequests],
        source_id=mlt_source_id,
        queue_rules=mlt_qrules,
        network_rules=mlt_netrules,
        opmon_conf=opmon_conf,
        data_subscriber=tc_subscriber,
        trigger_inputs_handler=tc_handler,
        mlt_conf=mlt_conf,
        standalone_candidate_maker_confs=tc_confs,
    )
    db.update_dal(mlt)

    if tpg_enabled:
        ta_subscriber = db.get_dal(class_name="DataReaderConf", uid="ta-subscriber-1")
        ta_handler = db.get_dal(class_name="DataHandlerConf", uid="def-ta-handler")

        tcmaker = dal.TriggerApplication(
            "tc-maker-1",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[tc_maker_control, triggerActivities, dataRequests],
            source_id=tc_source_id,
            queue_rules=tapp_qrules,
            network_rules=tapp_netrules,
            opmon_conf=opmon_conf,
            data_subscriber=ta_subscriber,
            trigger_inputs_handler=ta_handler,
        )
        db.update_dal(tcmaker)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller_service = dal.Service(
            "trg-controller_control", protocol="grpc", port=5700
        )
        db.update_dal(controller_service)
        controller = dal.RCApplication(
            "trg-controller",
            application_name="drunc-controller",
            opmon_conf=opmon_conf,
            runs_on=host,
            fsm=fsm,
            exposes_service=[controller_service],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"trg-segment",
            controller=controller,
            applications=[mlt] + ([tcmaker] if tpg_enabled else []),
        )
        db.update_dal(seg)

    db.commit()
    return


def generate_session(
    oksfile,
    include,
    session_name,
    op_env,
    connectivity_service_is_infrastructure_app=True,
    disable_connectivity_service=False
):
    """Simple script to create an OKS configuration file for a session.

      The file will automatically include the relevant schema files and
    any other OKS files you specify. Any necessary objects not supplied
    by included files will be generated and saved in the output file.

    """

    includefiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
    ]
    res, extra_includes = find_oksincludes(include, os.path.dirname(oksfile))
    if res:
        includefiles += extra_includes
    else:
        return

    dal = conffwk.dal.module("generated", includefiles)
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile} with includes {includefiles}")
    db.create_db(oksfile, includefiles)
    db.set_active(oksfile)

    hosts = []
    for vhost in db.get_dals(class_name="VirtualHost"):
        hosts.append(vhost.id)
        if vhost.id == "vlocalhost":
            host = vhost
    if "vlocalhost" not in hosts:
        cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
        db.update_dal(cpus)
        phdal = dal.PhysicalHost("localhost", contains=[cpus])
        db.update_dal(phdal)
        host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
        db.update_dal(host)
        hosts.append("vlocalhost")

    fsm = db.get_dal(class_name="FSMconfiguration", uid="fsmConf-test")
    controller_service = dal.Service(
        "root-controller_control", protocol="grpc", port=3333
    )
    db.update_dal(controller_service)
    controller = dal.RCApplication(
        "root-controller",
        application_name="drunc-controller",
        runs_on=host,
        fsm=fsm,
        exposes_service=[controller_service],
    )
    db.update_dal(controller)

    segments = db.get_dals(class_name="Segment")

    seg = dal.Segment(f"root-segment", controller=controller, segments=segments)
    db.update_dal(seg)

    detconf = db.get_dal(class_name="DetectorConfig", uid="dummy-detector")

    detconf.op_env = op_env
    db.update_dal(detconf)

    conn_svc_cfg = db.get_dal(class_name="ConnectivityService", uid="local-connectivity-service-config")
    opmon_svc = db.get_dal(class_name="OpMonURI", uid="local-opmon-uri")

    infrastructure_applications = []
    if connectivity_service_is_infrastructure_app:
        conn_svc = db.get_dal(class_name="ConnectionService", uid="local-connection-server")
        infrastructure_applications.append(conn_svc)

    sessiondal = dal.Session(
        session_name,
        environment=db.get_dal(
            class_name="VariableSet", uid="local-variables"
        ).contains,
        connectivity_service=conn_svc_cfg,
        segment=seg,
        detector_configuration=detconf,
        infrastructure_applications=infrastructure_applications,
        opmon_uri=opmon_svc,
    )
    db.update_dal(sessiondal)

    db.commit()
    return
