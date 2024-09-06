from calendar import day_abbr
from curses import qiflush
from re import S
import conffwk
import os
import glob
from daqconf.utils import find_oksincludes


def generate_hsi(
    oksfile,
    include,
    segment,
    session="",
):
    """Simple script to create an OKS configuration file for a FakeHSI segment.

    The file will automatically include the relevant schema files and
  any other OKS files you specify. Any necessary objects not supplied
  by included files will be generated and saved in the output file.

   Example:
     generate_hsiOKS -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs \
      hsiApps.data.xml

   Will load hosts, connections and moduleconfs data files and write the
  generated apps to hsiApps.data.xml.

     generate_hsiOKS --session --segment \
       -i appmodel/fsm -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs  \
       np04hsi-session.data.xml

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

    # Services
    hsi_control=db.get_dal(class_name="Service", uid="hsi-01_control")
    dataRequests = db.get_dal(class_name="Service", uid="dataRequests")
    tc_app_control = db.get_dal(class_name="Service", uid="hsi-to-tc-app_control")
    hsievents = db.get_dal(class_name="Service", uid="HSIEvents")

    # Source IDs
    hsi_source_id = db.get_dal(class_name="SourceIDConf", uid="hsi-srcid-01")
    hsi_tc_source_id = db.get_dal(class_name="SourceIDConf", uid="hsi-tc-srcid-1")

    # Queue Rules
    hsi_dlh_queue_rule=db.get_dal(class_name="QueueConnectionRule", uid="hsi-dlh-data-requests-queue-rule")
    hsi_qrules=[hsi_dlh_queue_rule]

    # Net Rules
    tc_net_rule=db.get_dal(class_name="NetworkConnectionRule", uid="tc-net-rule")
    hsi_rule=db.get_dal(class_name="NetworkConnectionRule", uid="hsi-rule")
    ts_hsi_net_rule = db.get_dal(class_name="NetworkConnectionRule", uid="ts-hsi-net-rule")
    data_req_hsi_net_rule=db.get_dal(class_name="NetworkConnectionRule", uid="data-req-hsi-net-rule")
    hsi_netrules = [hsi_rule, data_req_hsi_net_rule, ts_hsi_net_rule]
    tc_netrules = [hsi_rule, tc_net_rule]    

    hsi_handler = db.get_dal(class_name="DataHandlerConf", uid="def-hsi-handler")
    fakehsi = db.get_dal(class_name="FakeHSIEventGeneratorConf", uid="fakehsi")

    hsi = dal.FakeHSIApplication("hsi-01",
        runs_on=host,
        exposes_service = [hsi_control],
        source_id=hsi_source_id,
        queue_rules = hsi_qrules,
        network_rules = hsi_netrules,
        link_handler=hsi_handler,
        generator=fakehsi,
    )
    db.update_dal(hsi)

    hsi_to_tc_conf = db.get_dal(class_name="HSI2TCTranslatorConf", uid="hsi-to-tc-conf")

    hsi_to_tc = dal.HSIEventToTCApplication("hsi-to-tc-app",
        runs_on=host,
        exposes_service = [dataRequests, hsievents, tc_app_control],
        source_id = hsi_tc_source_id,
        network_rules = tc_netrules,
        hsievent_conf = hsi_to_tc_conf,
    )

    if segment or session != "":
        fsm = db.get_dal(class_name="FSMconfiguration", uid="FSMconfiguration_noAction")
        controller_service = dal.Service("hsi-controller_control", protocol="grpc", port=5800)
        db.update_dal(controller_service)
        controller = dal.RCApplication("hsi-controller", runs_on=host, fsm=fsm, exposes_service=[controller_service])
        db.update_dal(controller)


        seg = dal.Segment(f"hsi-segment", controller=controller, applications=[hsi, hsi_to_tc])
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

