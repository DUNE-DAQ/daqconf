from calendar import day_abbr
from curses import qiflush
from re import S
import conffwk
import os
import glob
from daqconf.utils import find_oksincludes


def generate_trigger(
    oksfile,
    include,
    segment,
    session="",
    tpg_enabled=True,
):
    """Simple script to create an OKS configuration file for a trigger segment.

    The file will automatically include the relevant schema files and
  any other OKS files you specify. Any necessary objects not supplied
  by included files will be generated and saved in the output file.

   Example:
     generate_triggerOKS -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs \
      triggerApps.data.xml

   Will load hosts, connections and moduleconfs data files and write the
  generated apps to triggerApps.data.xml.

     generate_triggerOKS --session --segment \
       -i appmodel/fsm -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs  \
       np04trigger-session.data.xml

   Will do the same but in addition it will generate a containing
  Segment for the apps and a containing Session for the Segment.

  NB: Currently FSM generation is not implemented so you must include
  an fsm file in order to generate a Segment

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
    tc_confs = [random_tc_generator]

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

    if segment or session != "":
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
            f"trg-segment", controller=controller, applications=[mlt] + ([tcmaker] if tpg_enabled else [])
        )
        db.update_dal(seg)

        if session != "":
            detconf = dal.DetectorConfig("dummy-detector")
            db.update_dal(detconf)
            sessiondal = dal.Session(
                f"{session}-session",
                segment=seg,
                detector_configuration=detconf,
            )
            db.update_dal(sessiondal)

    db.commit()
    return
