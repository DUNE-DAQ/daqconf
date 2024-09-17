from calendar import day_abbr
from curses import qiflush
from re import S
from wsgiref.validate import PartialIteratorWrapper
import conffwk
import os
import glob
from daqconf.utils import find_oksincludes


def generate_session(oksfile, include, session_name, op_env):
    """Simple script to create an OKS configuration file for a session.

    The file will automatically include the relevant schema files and
  any other OKS files you specify. Any necessary objects not supplied
  by included files will be generated and saved in the output file.

   Example:
     generate_sessionOKS --session_name test-session -i hosts \
       -i appmodel/connections.data.xml -i appmodel/moduleconfs \
      session.data.xml

   Will load hosts, connections and moduleconfs data files and write the
  generated session to session.data.xml.

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
    variables = db.get_dals(class_name="Variable")

    session_name_env = dal.Variable(
        "session-env-session-name-0", name="DUNEDAQ_SESSION", value=session_name
    )
    db.update_dal(session_name_env)
    partition_name_env = dal.Variable(
        "session-env-session-name-1", name="DUNEDAQ_PARTITION", value=session_name
    )
    db.update_dal(partition_name_env)
    cli_config = dal.Variable(
        "daqapp-cli-configuration",
        name="DAQAPP_CLI_CONFIG_SVC",
        value=f"oksconflibs:{oksfile}",
    )
    db.update_dal(cli_config)
    session_variables = [session_name_env, partition_name_env, cli_config]
    for var in variables:
        if "session-env" in var.id:
            session_variables.append(var)

    seg = dal.Segment(f"root-segment", controller=controller, segments=segments)
    db.update_dal(seg)

    detconf = db.get_dal(class_name="DetectorConfig", uid="dummy-detector")

    detconf.op_env = op_env
    db.update_dal(detconf)

    conn_svc = db.get_dal(class_name="ConnectionService", uid="local-connection-server")
    opmon_svc = db.get_dal(class_name="OpMonURI", uid="local-opmon-uri")

    sessiondal = dal.Session(
        session_name,
        environment=session_variables,
        segment=seg,
        detector_configuration=detconf,
        infrastructure_applications=[conn_svc],
        opmon_uri=opmon_svc,
    )
    db.update_dal(sessiondal)

    db.commit()
    return
