from dataclasses import dataclass
from daqconf.assets import resolve_asset_file
from daqconf.utils import find_oksincludes
import conffwk
import glob
import os
import traceback


def generate_dataflow(
    oksfile: str,
    include: list[str],
    n_dfapps: int,
    tpwriting_enabled: bool,
    generate_segment: bool,
    n_data_writers: int = 1,
    trmon_app: bool = False,
) -> None:
    """Simple script to create an OKS configuration file for a dataflow segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify.
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
    daqapp_control = db.get_dal(class_name="Service", uid="daqapp_control")
    rccontroller_control = db.get_dal(class_name="Service", uid="rccontroller_control")

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

    trmon_netrules = []
    trmon_qrules = []
    if trmon_app:
        trmon_req_net_rule = db.get_dal(
            class_name="NetworkConnectionRule", uid="trmon-req-net-rule"
        )
        trigger_record_net_rule = db.get_dal(
            class_name="NetworkConnectionRule", uid="trigger-record-net-rule"
        )
        dfapp_netrules.append(trmon_req_net_rule)
        dfapp_netrules.append(trigger_record_net_rule)

        trmon_netrules.append(trigger_record_net_rule)
        trigger_decision_token_q_rule = db.get_dal(
            class_name="QueueConnectionRule", uid="trigger-decision-token-q-rule"
        )
        trmon_qrules.append(trigger_decision_token_q_rule)

    dfo_netrules = [td_dfo_net_rule, ti_net_rule, df_token_net_rule]
    tpw_netrules = [tpset_net_rule]

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")

    dfo_conf = db.get_dal(class_name="DFOConf", uid="dfoconf-01")
    dfo = dal.DFOApplication(
        "dfo-01",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[daqapp_control],
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

        dfapp = dal.DFApplication(
            f"df-{dfapp_id:02}",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[daqapp_control],
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
            exposes_service=[daqapp_control],
            source_id=tpw_source_id,
            network_rules=tpw_netrules,
            opmon_conf=opmon_conf,
            tp_writer=tpw_writer_conf,
        )
        db.update_dal(tpwapp)
        tpwapps.append(tpwapp)

    trmonapps = []
    if trmon_app:
        trmonconf = db.get_dal(class_name="TRMonRequestorConf", uid="trmr-01")
        trmondwconf = db.get_dal(class_name="DataWriterConf", uid="tr_mon_dw-01")

        trmonapp = dal.TRMonReqApplication(
            "trmon-01",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[daqapp_control],
            network_rules=trmon_netrules,
            queue_rules=trmon_qrules,
            opmon_conf=opmon_conf,
            trmonreq=trmonconf,
            data_writer=trmondwconf,
            uses=dfhw,
        )
        db.update_dal(trmonapp)
        trmonapps.append(trmonapp)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller = dal.RCApplication(
            "df-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[rccontroller_control],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"df-segment",
            controller=controller,
            applications=[dfo] + dfapps + tpwapps + trmonapps,
        )
        db.update_dal(seg)

    try:
        db.commit()
    except RuntimeError as err:
        print("Failed to commit Dataflow DB!")
        print(traceback.format_exc())
        raise err
    return


def generate_hsi(
    oksfile: str,
    include: list[str],
    generate_segment: bool,
) -> None:
    """Simple script to create an OKS configuration file for a FakeHSI segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify.


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
    daqapp_control = db.get_dal(class_name="Service", uid="daqapp_control")
    rccontroller_control = db.get_dal(class_name="Service", uid="rccontroller_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
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
        exposes_service=[daqapp_control],
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
        exposes_service=[dataRequests, hsievents, daqapp_control],
        source_id=hsi_tc_source_id,
        network_rules=tc_netrules,
        opmon_conf=opmon_conf,
        hsevent_to_tc_conf=hsi_to_tc_conf,
    )
    db.update_dal(hsi_to_tc)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller = dal.RCApplication(
            "hsi-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[rccontroller_control],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"hsi-segment", controller=controller, applications=[hsi, hsi_to_tc]
        )
        db.update_dal(seg)

    db.commit()
    return


def generate_readout(
    readoutmap: str,
    oksfile: str,
    include: list[str],
    generate_segment: bool,
    emulated_file_name: str,
    tpg_enabled: bool = True,
    hosts_to_use: list[str] = [],
) -> None:
    """Simple script to create an OKS configuration file for all
  ReadoutApplications defined in a readout map.

    The file will automatically include the relevant schema files and
  any other OKS files you specify.

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

    includefiles = (
        [
            "schema/confmodel/dunedaq.schema.xml",
            "schema/appmodel/application.schema.xml",
            "schema/appmodel/trigger.schema.xml",
            "schema/appmodel/fdmodules.schema.xml",
            "schema/appmodel/wiec.schema.xml",
        ]
        + [readoutmap]
        if os.path.exists(readoutmap)
        else []
    )

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
    daqapp_control = db.get_dal(class_name="Service", uid="daqapp_control")
    rccontroller_control = db.get_dal(class_name="Service", uid="rccontroller_control")

    try:
        rule = db.get_dal(
            class_name="NetworkConnectionRule", uid="data-req-readout-net-rule"
        )
    except:
        print(
            'Expected NetworkConnectionRule "data-req-readout-net-rule" not found in input databases!'
        )
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
        print(
            'Expected QueueConnectionRule "fd-dlh-data-requests-queue-rule" not found in input databases!'
        )
    else:
        qrules = [rule]
        for rule in [
            "fa-queue-rule",
            "tp-queue-rule",
        ]:
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
    fragagg = db.get_dal(class_name="FragmentAggregatorConf", uid="frag-agg-01")

    appnum = 0
    nicrec = None
    flxcard = None
    wm_conf = None
    hermes_conf = None
    ruapps = []
    for connection in detector_connections:

        geo_id = connection.get("GeoId")
        det_id = geo_id[0].detector_id
        if det_id == 0:
            raise Exception(f"Unable to determine detector ID from Hardware Map!")

        tphandler = db.get_dal(class_name="DataHandlerConf", uid="def-tp-handler")

        if det_id == 2:
            if "DAPHNEStream" in emulated_file_name:
                linkhandler = db.get_dal(
                    class_name="DataHandlerConf", uid="def-pds-stream-link-handler"
                )
                cb_desc = db.get_dal(
                    class_name="DataMoveCallbackDescriptor", uid="pds-stream-raw-input"
                )
            else:
                linkhandler = db.get_dal(
                    class_name="DataHandlerConf", uid="def-pds-link-handler"
                )
                cb_desc = db.get_dal(
                    class_name="DataMoveCallbackDescriptor", uid="pds-raw-input"
                )

        elif det_id == 3 or det_id == 10:
            linkhandler = db.get_dal(
                class_name="DataHandlerConf", uid="def-link-handler"
            )
            cb_desc = db.get_dal(
                class_name="DataMoveCallbackDescriptor", uid="wib-eth-raw-input"
            )
        elif det_id == 11:
            linkhandler = db.get_dal(
                class_name="DataHandlerConf", uid="def-tde-link-handler"
            )
            cb_desc = db.get_dal(
                class_name="DataMoveCallbackDescriptor", uid="tde-raw-input"
            )
        elif det_id == 12:
            linkhandler = db.get_dal(
                class_name="DataHandlerConf", uid="def-crt-bern-link-handler"
            )
            # Not used, but needed for ReadoutApplication
            cb_desc = db.get_dal(
                class_name="DataMoveCallbackDescriptor", uid="crt-bern-raw-input"
            )
        elif det_id == 13:
            linkhandler = db.get_dal(
                class_name="DataHandlerConf", uid="def-crt-grenoble-link-handler"
            )
            # Not used, but needed for ReadoutApplication
            cb_desc = db.get_dal(
                class_name="DataMoveCallbackDescriptor", uid="crt-grenoble-raw-input"
            )

        hostnum = appnum % len(hosts)
        # print(f"Looking up host[{hostnum}] ({hosts[hostnum]})")
        host = db.get_dal(class_name="VirtualHost", uid=hosts[hostnum])

        # Find which type of DataReceiver we need for this connection
        if connection.className() == "NetworkDetectorToDaqConnection":
            receiver = connection.net_receiver
        elif connection.className() == "FelixDetectorToDaqConnection":
            receiver = connection.felix_receiver

        # Action Plans
        readout_start = db.get_dal(class_name="ActionPlan", uid="readout-start")
        readout_stop = db.get_dal(class_name="ActionPlan", uid="readout-stop")

        # Emulated stream
        if type(receiver).__name__ == "FakeDataReceiver":
            if nicrec == None:
                try:
                    stream_emu = db.get_dal(
                        class_name="StreamEmulationParameters", uid="stream-emu"
                    )
                    stream_emu.data_file_name = resolve_asset_file(emulated_file_name)
                    db.update_dal(stream_emu)
                except:
                    stream_emu = dal.StreamEmulationParameters(
                        "stream-emu",
                        data_file_name=resolve_asset_file(emulated_file_name),
                        input_file_size_limit=5777280,
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
                    print(
                        'Expected WIBModuleConf "def-wib-conf" not found in input databases!'
                    )
            if hermes_conf == None:
                try:
                    hermes_conf = db.get_dal("HermesModuleConf", "def-hermes-conf")
                except:
                    print(
                        'Expected HermesModuleConf "def-hermes-conf" not found in input databases!'
                    )

            datareader = nicrec

            wiec_app = dal.WIECApplication(
                f"wiec-{connection.id}",
                application_name="daq_application",
                runs_on=host,
                detector_connections=[connection],
                wib_module_conf=wm_conf,
                hermes_module_conf=hermes_conf,
                exposes_service=[daqapp_control],
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
        elif type(receiver).__name__ == "FileReaderReceiver":
            if nicrec == None:
                try:
                    snb_files = db.get_dal(
                        class_name="SNBFileSourceParameters",
                        uid=f"snb-files-{connection.id}",
                    )
                    snb_files.data_files = [resolve_asset_file(emulated_file_name)]
                    db.update_dal(snb_files)
                except:
                    snb_files = dal.SNBFileSourceParameters(
                        "snb-files-0",
                        data_files=[resolve_asset_file(emulated_file_name)],
                        input_buffer_size=5777280,
                        file_compression_algorithm="None",
                    )
                    db.update_dal(snb_files)

                print("Generating fake DataReaderConf")
                nicrec = dal.SNBFileReaderConf(
                    f"nicrcvr-file-reader",
                    template_for="SNBFileReaderModule",
                    emulation_mode=1,
                    snb_conf=snb_files,
                )
                db.update_dal(nicrec)
            datareader = nicrec

            print(f"Using SNB DataHandler")
            linkhandler.template_for = "SNBDataHandlerModule"
            db.update_dal(linkhandler)

            readout_start = db.get_dal(class_name="ActionPlan", uid="snb-readout-start")
            readout_stop = db.get_dal(class_name="ActionPlan", uid="snb-readout-stop")
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

        ru = dal.ReadoutApplication(
            f"ru-{connection.id}",
            application_name="daq_application",
            runs_on=host,
            detector_connections=[connection],
            network_rules=netrules,
            queue_rules=qrules,
            link_handler=linkhandler,
            data_reader=datareader,
            fragment_aggregator=fragagg,
            opmon_conf=opmon_conf,
            tp_generation_enabled=tpg_enabled,
            ta_generation_enabled=tpg_enabled,
            uses=rohw,
            exposes_service=[daqapp_control, dataRequests, timeSyncs],
            action_plans=[readout_start, readout_stop],
            callback_desc=cb_desc,
        )
        if tpg_enabled:
            ru.tp_handler = tphandler
            tp_sources = []
            tpbaseid = (appnum * 3) + 100
            # 30-Apr-2025, KAB: added support for 1 "plane" of non-TPC TPs (e.g. PDS).
            # That is compared with the usual 3 planes of TPs for TPC detectors.
            for plane in range(1 if det_id not in [3, 10, 11] else 3):
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
        controller = dal.RCApplication(
            "ru-controller",
            application_name="drunc-controller",
            runs_on=host,
            fsm=fsm,
            opmon_conf=opmon_conf,
            exposes_service=[rccontroller_control],
        )
        db.update_dal(controller)
        db.commit()

        seg = dal.Segment(f"ru-segment", controller=controller, applications=ruapps)
        db.update_dal(seg)
        db.commit()

    db.commit()
    return


def generate_fakedata(
    oksfile: str,
    include: list[str],
    generate_segment: bool,
    n_streams: int,
    n_apps: int,
    det_id: int,
    fragment_type: str | None = None,
) -> None:
    """Simple script to create an OKS configuration file for a FakeDataProd-based readout segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify.

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

    source_id = 0
    fakeapps = []
    # Services
    daqapp_control = db.get_dal(class_name="Service", uid="daqapp_control")
    rccontroller_control = db.get_dal(class_name="Service", uid="rccontroller_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
    timeSyncs = db.get_dal(class_name="Service", uid="timeSyncs")
    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")
    fragagg = db.get_dal(class_name="FragmentAggregatorConf", uid="frag-agg-01")

    rule = db.get_dal(
        class_name="NetworkConnectionRule", uid="data-req-readout-net-rule"
    )
    netrules = [rule]
    for rule in ["ts-fdp-net-rule"]:
        netrules.append(db.get_dal(class_name="NetworkConnectionRule", uid=rule))

    try:
        rule = db.get_dal(
            class_name="QueueConnectionRule", uid="fpdm-data-requests-queue-rule"
        )
    except:
        print(
            'Expected QueueConnectionRule "fpdm-data-requests-queue-rule" not found in input databases!'
        )
    else:
        qrules = [rule]
        for rule in [
            "fa-queue-rule",
        ]:
            qrules.append(db.get_dal(class_name="QueueConnectionRule", uid=rule))

    frame_size = 0
    if det_id == 3:
        frame_size = 7200
        time_tick_diff = 32 * 64
        response_delay = 0
        fragment_type = "WIBEth"
    elif det_id == 2:
        if fragment_type == "DAPHNEEthStream":
            frame_size = 2008
            time_tick_diff = 280
            response_delay = 0
        elif fragment_type == "DAPHNEEth":
            frame_size = 1864
            time_tick_diff = 1024
            response_delay = 0
        else:
            raise Exception(
                f"FakeDataProd fragment_type '{fragment_type}' not recognized for detector ID {det_id}; "
                f"expected 'DAPHNEEthStream' or 'DAPHNEEth'"
            )
    else:
        raise Exception(
            f"FakeDataProd parameters not configured for detector ID {det_id}"
        )

    for appidx in range(n_apps):

        fakeapp = dal.FakeDataApplication(
            f"fakedata_{appidx}",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[daqapp_control, dataRequests, timeSyncs],
            queue_rules=qrules,
            network_rules=netrules,
            fragment_aggregator=fragagg,
            opmon_conf=opmon_conf,
        )

        for streamidx in range(n_streams):
            stream = dal.FakeDataProdConf(
                f"fakedata_{appidx}_stream_{streamidx}",
                system_type="Detector_Readout",
                source_id=source_id,
                time_tick_diff=time_tick_diff,
                frame_size=frame_size,
                response_delay=response_delay,
                fragment_type=fragment_type,
            )
            db.update_dal(stream)
            fakeapp.producers.append(stream)
            source_id = source_id + 1

        db.update_dal(fakeapp)
        fakeapps.append(fakeapp)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller = dal.RCApplication(
            "ru-controller",
            application_name="drunc-controller",
            opmon_conf=opmon_conf,
            runs_on=host,
            fsm=fsm,
            exposes_service=[rccontroller_control],
        )
        db.update_dal(controller)

        seg = dal.Segment(
            f"ru-segment",
            controller=controller,
            applications=fakeapps,
        )
        db.update_dal(seg)

    db.commit()
    return


def generate_trigger(
    oksfile: str,
    include: list[str],
    generate_segment: bool,
    tpg_enabled: bool = True,
    hsi_enabled: bool = False,
) -> None:
    """Simple script to create an OKS configuration file for a trigger segment.

      The file will automatically include the relevant schema files and
    any other OKS files you specify.

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
    daqapp_control = db.get_dal(class_name="Service", uid="daqapp_control")
    rccontroller_control = db.get_dal(class_name="Service", uid="rccontroller_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
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
    tc_confs = []

    try:
        fixedtime_tc_generator = db.get_dal(
            class_name="FixedTimeTCMakerModuleConf",
            uid="ft-trig-conf",
        )
        print(
            f"FixedTimeTCMakerModule has been configured, disabling random triggers and HSI"
        )
        tc_confs = [fixedtime_tc_generator]
    except:
        pass  # No FixedTimeTCMaker
    if not hsi_enabled and len(tc_confs) == 0:
        tc_confs = [random_tc_generator]

    mlt = dal.MLTApplication(
        "mlt",
        runs_on=host,
        application_name="daq_application",
        exposes_service=[
            daqapp_control,
            triggerCandidates,
            triggerInhibits,
            dataRequests,
        ],
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

        # Action Plans
        tc_maker_start = db.get_dal(class_name="ActionPlan", uid="tc-maker-start")

        tcmaker = dal.TriggerApplication(
            "tc-maker-1",
            runs_on=host,
            application_name="daq_application",
            exposes_service=[daqapp_control, triggerActivities, dataRequests],
            source_id=tc_source_id,
            queue_rules=tapp_qrules,
            network_rules=tapp_netrules,
            opmon_conf=opmon_conf,
            data_subscriber=ta_subscriber,
            trigger_inputs_handler=ta_handler,
            action_plans=[tc_maker_start],
        )
        db.update_dal(tcmaker)

    if generate_segment:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller = dal.RCApplication(
            "trg-controller",
            application_name="drunc-controller",
            opmon_conf=opmon_conf,
            runs_on=host,
            fsm=fsm,
            exposes_service=[rccontroller_control],
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
    oksfile: str,
    include: list[str],
    session_name: str,
    op_env: str,
    connectivity_service_is_infrastructure_app: bool = True,
) -> None:
    """Simple script to create an OKS configuration file for a session.

      The file will automatically include the relevant schema files and
    any other OKS files you specify.

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

    opmon_conf = db.get_dal(class_name="OpMonConf", uid="slow-all-monitoring")

    fsm = db.get_dal(class_name="FSMconfiguration", uid="fsmConf-test")
    rccontroller_control = db.get_dal(class_name="Service", uid="root-rccontroller_control")
    controller = dal.RCApplication(
        "root-controller",
        application_name="drunc-controller",
        runs_on=host,
        fsm=fsm,
        opmon_conf=opmon_conf,
        exposes_service=[rccontroller_control],
    )
    db.update_dal(controller)

    segments = db.get_dals(class_name="Segment")

    seg = dal.Segment(f"root-segment", controller=controller, segments=segments)
    db.update_dal(seg)

    detconf = db.get_dal(class_name="DetectorConfig", uid="dummy-detector")

    detconf.op_env = op_env
    db.update_dal(detconf)

    opmon_svc = db.get_dal(class_name="OpMonURI", uid="local-opmon-uri")

    trace_file_var = None
    TRACE_FILE = os.getenv("TRACE_FILE")
    if TRACE_FILE is not None:
        trace_file_var = dal.Variable(
            "session-env-trace-file", name="TRACE_FILE", value=TRACE_FILE
        )
        db.update_dal(trace_file_var)

    infrastructure_applications = []
    if connectivity_service_is_infrastructure_app:
        conn_svc = db.get_dal(
            class_name="ConnectionService", uid="local-connection-server"
        )
        infrastructure_applications.append(conn_svc)

    env_vars_for_local_running = db.get_dal(
        class_name="VariableSet", uid="local-variables"
    ).contains
    if trace_file_var is not None:
        env_vars_for_local_running.append(trace_file_var)

    sessiondal = dal.Session(
        session_name,
        environment=env_vars_for_local_running,
        segment=seg,
        detector_configuration=detconf,
        infrastructure_applications=infrastructure_applications,
        opmon_uri=opmon_svc,
    )

    conn_svc_cfg = db.get_dal(
        class_name="ConnectivityService", uid="local-connectivity-service-config"
    )
    sessiondal.connectivity_service = conn_svc_cfg

    db.update_dal(sessiondal)

    db.commit()
    return
