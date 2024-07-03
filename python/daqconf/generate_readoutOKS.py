from calendar import day_abbr
from curses import qiflush
import conffwk
import os
import glob
from daqconf.assets import resolve_asset_file


def generate_readout(
    readoutmap,
    oksfile,
    include,
    segment,
    session,
    emulated_file_name="asset://?checksum=e96fd6efd3f98a9a3bfaba32975b476e",
    tpg_enabled=True,
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

    dal = conffwk.dal.module("generated", includefiles[4])
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)

    detector_connections = db.get_dals(class_name="DetectorToDaqConnection")

    # Check tpg_enabled here, if it is False, then we want to make our own RawDataProcessor
    if len(db.get_dals(class_name="LatencyBuffer")) > 0 and tpg_enabled:
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
            "lb-1",
            numa_aware=True,
            numa_node=1,
            size=139008,
            alignment_size=4096,
            intrinsic_allocator=True,
        )
        db.update_dal(latencybuffer)
        dataproc = dal.RawDataProcessor(
            "dataproc-1",
            max_ticks_tot=10000,
            mask_processing=False,            
            algorithm="SimpleThreshold",
            threshold=1900,
            channel_map="PD2HDChannelMap",
            tpg_enabled=tpg_enabled,
        )
                    
        db.update_dal(dataproc)
        linkhandler = dal.DataHandlerConf(
            "linkhandler-1",
            template_for="FDDataHandlerModule",
            input_data_type="WIBEthFrame",
            request_handler=reqhandler,
            latency_buffer=latencybuffer,
            data_processor=dataproc,
        )
        db.update_dal(linkhandler)
        tphandler = dal.DataHandlerConf(
            "tphandler-1",
            template_for="TriggerDataHandlerModule",
            input_data_type="TriggerPrimitive",
            request_handler=reqhandler,
            latency_buffer=latencybuffer,
            data_processor=dataproc,
        )
        db.update_dal(tphandler)
    try:
        rule = db.get_dal(class_name="NetworkConnectionRule", uid="data-req-net-rule")
    except:
        # Failed to get rule, now we have to invent some
        netrules = generate_net_rules(dal, db)
    else:
        netrules = [rule]
        # Assume we have all the other rules we need
        for rule in ["tp-net-rule", "ts-net-rule", "ta-net-rule"]:
            netrules.append(db.get_dal(class_name="NetworkConnectionRule", uid=rule))

    try:
        rule = db.get_dal(
            class_name="QueueConnectionRule", uid="data-requests-queue-rule"
        )
    except:
        qrules = generate_queue_rules(dal, db)
    else:
        qrules = [rule]
        for rule in ["fa-queue-rule", "wib-eth-raw-data-rule", "tp-queue-rule"]:
            qrules.append(db.get_dal(class_name="QueueConnectionRule", uid=rule))

    hosts = []
    for host in db.get_dals(class_name="VirtualHost"):
        hosts.append(host.id)
    if "vlocalhost" not in hosts:
        cpus = dal.ProcessingResource("cpus", cpu_cores=[0, 1, 2, 3])
        db.update_dal(cpus)
        phdal = dal.PhysicalHost("localhost", contains=[cpus])
        db.update_dal(phdal)
        host = dal.VirtualHost("vlocalhost", runs_on=phdal, uses=[cpus])
        db.update_dal(host)
        hosts.append("vlocalhost")

    rohw = dal.RoHwConfig(f"rohw-{detector_connections[0].id}")
    db.update_dal(rohw)

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

        for resource in connection.contains:
            if type(resource).__name__ == "ResourceSetAND":
                rog = resource
            else:
                receiver = resource
        # Emulated stream
        if type(receiver).__name__ == "ReadoutInterface":
            if nicrec == None:
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
                print("Generating fake DPDKReaderConf")
                nicrec = dal.DPDKReaderConf(
                    f"nicrcvr-1",
                    template_for="FDFakeCardReader",
                    emulation_mode=1,
                    emulation_conf=stream_emu,
                )
                db.update_dal(nicrec)
            datareader = nicrec
        elif type(receiver).__name__ == "DPDKReceiver":
            if nicrec == None:
                print("Generating DPDKReaderConf")
                nicrec = dal.DPDKReaderConf(f"nicrcvr-1", template_for="DPDKReaderModule")
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
            wiec_app = dal.WIECApplication(
                f"wiec-{connection.id}",
                runs_on=host,
                contains=[connection],
                wib_module_conf=wm_conf,
                hermes_module_conf=hermes_conf
            )
            db.update_dal(wiec_app)


        elif type(receiver).__name__ == "FelixInterface":
            if flxcard == None:
                print("Generating Felix DataReaderConf")
                flxcard = dal.DataReaderConf(
                    f"flxConf-1", template_for="FelixCardReader"
                )
                db.update_dal(flxcard)
            datareader = flxcard
        else :
            print(f"ReadoutGroup contains unknown interface type {type(receiver).__name__}")
            continue

        ru = dal.ReadoutApplication(
            f"ru-{rog.id}",
            runs_on=host,
            contains=[rog],
            network_rules=netrules,
            queue_rules=qrules,
            link_handler=linkhandler,
            data_reader=datareader,
            uses=rohw,
        )
        if tpg_enabled:
            ru.tp_handler = tphandler
            ru.tp_source_id=appnum + 100
            ru.ta_source_id=appnum + 1000
        appnum = appnum + 1
        print(f"{ru=}")
        db.update_dal(ru)
        ruapps.append(ru)
    if appnum == 0:
        print(f"No ReadoutApplications generated\n")
        return



    if segment or session:
        fsm = db.get_dal(class_name="FSMconfiguration", uid="fsmConf-1")
        controller = dal.RCApplication("ru-controller", runs_on=host, fsm=fsm)
        db.update_dal(controller)
        seg = dal.Segment(f"ru-segment", controller=controller, applications=ruapps)
        db.update_dal(seg)

        if session:
            ro_maps = db.get_dals(class_name="ReadoutMap")
            detconf = dal.DetectorConfig("dummy-detector")
            db.update_dal(detconf)
            sessname = os.path.basename(readoutmap).removesuffix(".data.xml")
            sessiondal = dal.Session(
                f"{sessname}-session",
                segment=seg,
                detector_configuration=detconf,
                readout_map=ro_maps[0],
            )
            db.update_dal(sessiondal)

    db.commit()
    return


def generate_net_rules(dal, db):
    print(f"Generating network rules")
    netrules = []
    dataservice = dal.Service("dataFragments", port=0)
    db.update_dal(dataservice)
    tpservice = dal.Service("triggerPrimitives", port=0)
    db.update_dal(tpservice)
    timeservice = dal.Service("timeSync", port=0)
    db.update_dal(timeservice)

    newdescr = dal.NetworkConnectionDescriptor(
        "fa-net-descr",
        uid_base="data_requests_for_",
        connection_type="kSendRecv",
        data_type="DataRequest",
        associated_service=dataservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "fa-net-rule", endpoint_class="FragmentAggregatorModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "ta-net-descr",
        uid_base="ta_",
        connection_type="kPubSub",
        data_type="TriggerActivity",
        associated_service=dataservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "ta-net-rule", endpoint_class="DataSubscriberModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "tp-net-descr",
        uid_base="trigger_primitive_data_request",
        connection_type="kPubSub",
        data_type="TPSet",
        associated_service=tpservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "tp-net-rule", endpoint_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)

    newdescr = dal.NetworkConnectionDescriptor(
        "ts-net-descr",
        uid_base="timeSync",
        connection_type="kPubSub",
        data_type="TimeSync",
        associated_service=timeservice,
    )
    db.update_dal(newdescr)
    newrule = dal.NetworkConnectionRule(
        "ts-net-rule", endpoint_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    netrules.append(newrule)
    return netrules


def generate_queue_rules(dal, db):
    qrules = []
    newdescr = dal.QueueDescriptor(
        "dataRequest", queue_type="kFollySPSCQueue", data_type="DataRequest", uid_base="data_reqs_for_"
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "data-requests-queue-rule",
        destination_class="FDDataHandlerModule",
        descriptor=newdescr,
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "aggregatorInput", queue_type="kFollyMPMCQueue", data_type="Fragment", uid_base="fragments_from_"
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "fa-queue-rule",
        destination_class="FragmentAggregatorModule",
        descriptor=newdescr,
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "rawWIBInput", queue_type="kFollySPSCQueue", data_type="WIBEthFrame", uid_base="raw_"
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "rawInputRule", destination_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    newdescr = dal.QueueDescriptor(
        "tpInput",
        queue_type="kFollyMPMCQueue",
        capacity=100000,
        data_type="TriggerPrimitive",
        uid_base="tps_"        
    )
    db.update_dal(newdescr)
    newrule = dal.QueueConnectionRule(
        "tpRule", destination_class="FDDataHandlerModule", descriptor=newdescr
    )
    db.update_dal(newrule)
    qrules.append(newrule)

    return qrules

def generate_wibmoduleconf(dal, db):
    try:
        femb_settings = db.get_dal("FEMBSettings", "def-femb-settings")
    except:
        femb_settings = dal.FEMBSettings(
            "def-femb-settings")
        db.update_dal(femb_settings)

    try:
        coldadc_settings = db.get_dal("ColdADCSettings", "def-coldadc-settings")
    except:
        coldadc_settings = dal.ColdADCSettings(
            "def-coldadc-settings")
        db.update_dal(coldadc_settings)
    try:
        wibpulser = db.get_dal("WIBPulserSettings", "def-wib-pulser-setting")
    except:
        wibpulser = dal.WIBPulserSettings(
            "def-wib-pulser-setting")
        db.update_dal(wibpulser)

    wib_settings = dal.WIBSettings(
        "def-wib-settings",
        femb0 = femb_settings,
        femb1 = femb_settings,
        femb2 = femb_settings,
        femb3 = femb_settings,
        coldadc_settings = coldadc_settings,
        wib_pulser = wibpulser
    )
    db.update_dal(wib_settings)
    wm_conf=dal.WIBModuleConf(
        "def-wibmodule-conf",
        settings = wib_settings)
    db.update_dal(wm_conf)
    return wm_conf

def generate_hermesmoduleconf(dal, db):
    try:
        addr_table = db.get_dal("IpbusAddressTable", "Hermes-addrtab")
    except:
        addr_table = dal.IpbusAddressTable("Hermes-addrtab")
        db.update_dal(addr_table)

    hermes_conf=dal.HermesModuleConf(
        "def-hermes-conf",
        address_table = addr_table)
    db.update_dal(hermes_conf)
    return hermes_conf
