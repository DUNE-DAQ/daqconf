from calendar import day_abbr
from curses import qiflush
from re import S
import conffwk
import os
import glob
from daqconf.utils import find_oksincludes


def generate_dataflow(
    oksfile,
    include,
    n_dfapps,
    tpwriting_enabled,
    segment,
    session: str = "",
):
    """Simple script to create an OKS configuration file for a dataflow segment.

    The file will automatically include the relevant schema files and
  any other OKS files you specify. Any necessary objects not supplied
  by included files will be generated and saved in the output file.

   Example:
     generate_dataflowOKS -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs \
      dataflowApps.data.xml

   Will load hosts, connections and moduleconfs data files and write the
  generated apps to dataflowApps.data.xml.

     generate_dataflowOKS --session --segment \
       -i appmodel/fsm -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs  \
       np04dataflow-session.data.xml

   Will do the same but in addition it will generate a containing
  Segment for the apps and a containing Session for the Segment.

  NB: Currently FSM generation is not implemented so you must include
  an fsm file in order to generate a Segment

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
            f"df-{dfapp_id:02}_control", protocol="rest", port=5601 + dfapp_id
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
            data_writers=[dw_conf],
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

    if segment or session != "":
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
