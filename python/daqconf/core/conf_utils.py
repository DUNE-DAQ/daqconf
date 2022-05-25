# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

from os.path import exists, join
from rich.console import Console
from copy import deepcopy
from collections import namedtuple, defaultdict
import json
import os
from enum import Enum
from graphviz import Digraph
import networkx as nx
import moo.otypes
import copy as cp
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('networkmanager/nwmgr.jsonnet')
moo.otypes.load_types('iomanager/connection.jsonnet')

from appfwk.utils import acmd, mcmd, mspec
import dunedaq.appfwk.app as appfwk  # AddressedCmd,
import dunedaq.rcif.cmd as rccmd  # AddressedCmd,
import dunedaq.networkmanager.nwmgr as nwmgr
import dunedaq.iomanager.connection as conn

from daqconf.core.daqmodule import DAQModule

console = Console()

########################################################################
#
# Classes
#
########################################################################

# TODO: Understand whether extra_commands is actually needed. Seems like "resume" is already being sent to everyone?

# TODO: Make these all dataclasses

class Direction(Enum):
    IN = 1
    OUT = 2

class Endpoint:
    # def __init__(self, **kwargs):
    #     if kwargs['connection']:
    #         self.__init_with_nwmgr(**kwargs)
    #     else:
    #         self.__init_with_external_name(**kwargs)
    def __init__(self, external_name, internal_name, direction, topic=[], size_hint=1000):
        self.external_name = external_name
        self.internal_name = internal_name
        self.direction = direction
        self.topic = topic
        self.size_hint = size_hint

    def __repr__(self):
        return f"{self.external_name}/{self.internal_name}"
    # def __init_with_nwmgr(self, connection, internal_name):
    #     self.nwmgr_connection = connection
    #     self.internal_name = internal_name
    #     self.external_name = None
    #     self.direction = Direction.IN

class ExternalConnection(Endpoint):
   def __init__(self, external_name, internal_name, direction, host, port, topic=[]):
        super().__init__(external_name, internal_name, direction, topic)
        self.host = host
        self.port = port

class Queue:
    def __init__(self, push_module, pop_module, name = None, size=10, toposort=False):
        self.name = name
        self.size = size
        self.push_modules = [push_module]
        self.pop_modules = [pop_module]
        self.toposort = toposort
        if self.name is None:
            self.name = push_module + "_to_" + pop_module

    def add_module_link(self, push_module, pop_module):
        if push_module not in self.push_modules:
            self.push_modules.append(push_module)
        if pop_module not in self.pop_modules:
            self.pop_modules.append(pop_module)

    def __repr__(self):
        return self.name

GeoID = namedtuple('GeoID', ['system', 'region', 'element'])
FragmentProducer = namedtuple('FragmentProducer', ['geoid', 'requests_in', 'fragments_out', 'queue_name'])


Publisher = namedtuple(
    "Publisher", ['msg_type', 'msg_module_name', 'subscribers'])

Sender = namedtuple("Sender", ['msg_type', 'msg_module_name', 'receiver'])

# AppConnection = namedtuple("AppConnection", ['nwmgr_connection', 'receivers', 'topics', 'msg_type', 'msg_module_name', 'use_nwqa'], defaults=[None, None, True])
AppConnection = namedtuple("AppConnection", ['bind_apps', 'connect_apps'], defaults=[[],[]])

########################################################################
#
# Functions
#
########################################################################

def make_module_deps(app, system_connections, verbose=False):
    """
    Given a list of `module` objects, produce a dictionary giving
    the dependencies between them. A dependency is any connection between
    modules. Connections whose upstream ends begin with a '!' are not
    considered dependencies, to allow us to break cycles in the DAG.

    Returns a networkx DiGraph object where nodes are module names
    """

    deps = nx.DiGraph()
    for module in app.modulegraph.modules:
        deps.add_node(module.name)

        for endpoint in app.modulegraph.endpoints:
            if endpoint.internal_name is None or endpoint.direction != Direction.IN:
                continue
            mod_name, q_name = endpoint.internal_name.split(".")
            if module.name != mod_name:
                continue
            is_queue = False
            for connection in system_connections:
                if connection.uid == endpoint.external_name and connection.service_type == "kQueue":
                    is_queue = True
                    break

            for other_endpoint in app.modulegraph.endpoints:
                if other_endpoint.external_name == endpoint.external_name and other_endpoint.internal_name != endpoint.internal_name and other_endpoint.direction != Direction.IN:
                    other_mod, other_q = other_endpoint.internal_name.split(".")
                    if verbose: console.log(f"Adding generated dependency edge {other_mod} -> {mod_name}")
                    deps.add_edge(other_mod, mod_name)


    for queue in app.modulegraph.queues:
        if not queue.toposort:
            continue
        for push_addr in queue.push_modules:
            for pop_addr in queue.pop_modules:
                push_mod, push_name = push_addr.split(".", maxsplit=1)
                pop_mod, pop_name = pop_addr.split(".", maxsplit=1)
                if verbose: console.log(f"Adding queue dependency edge {push_mod} -> {pop_mod}")
                deps.add_edge(push_mod, pop_mod)



    return deps


def make_app_deps(the_system, verbose=False):
    """
    Produce a dictionary giving
    the dependencies between a set of applications, given their connections.

    Returns a networkx DiGraph object where nodes are app names
    """

    deps = nx.DiGraph()

    for app in the_system.apps.keys():
        deps.add_node(app)

    if verbose: console.log("make_apps_deps()")
    for from_endpoint, conn in the_system.app_connections.items():
        from_app = from_endpoint.split(".")[0]
        if hasattr(conn, "subscribers"):
            for to_app in [ds.split(".")[0] for ds in conn.subscribers]:
                if verbose: console.log(f"subscribers: {from_app}, {to_app}")
                deps.add_edge(from_app, to_app)
        elif hasattr(conn, "receiver"):
            to_app = conn.receiver.split(".")[0]
            if verbose: console.log(f"receiver: {from_app}, {to_app}")
            deps.add_edge(from_app, to_app)

    return deps

def add_one_command_data(command_data, command, default_params, app, module_order):
    """Add the command data for one command in one app to the command_data object. The modules to be sent the command are listed in `module_order`. If the module has an entry in its extra_commands dictionary for this command, then that entry is used as the parameters to pass to the command, otherwise the `default_params` object is passed"""
    mod_and_params=[]
    for module in module_order:
        extra_commands = app.modulegraph.get_module(module).extra_commands
        if command in extra_commands:
            mod_and_params.append((module, extra_commands[command]))
        else:
            mod_and_params.append((module, default_params))

    command_data[command] = acmd(mod_and_params)

def make_queue_connection(the_system, app, endpoint_name, in_apps, out_apps, size, verbose):
    if len(in_apps) == 1 and len(out_apps) == 1:
        if verbose:
            console.log(f"Connection {endpoint_name}, SPSC Queue")
        the_system.connections[app] += [conn.ConnectionId(uid=endpoint_name, service_type="kQueue", data_type="", uri=f"queue://FollySPSC:{size}")]
    else:
        if verbose:
            console.log(f"Connection {endpoint_name}, MPMC Queue")
        the_system.connections[app] += [conn.ConnectionId(uid=endpoint_name, service_type="kQueue", data_type="", uri=f"queue://FollyMPMC:{size}")]

def make_external_connection(the_system, endpoint_name, app_name, host, port, topic, inout, verbose):
    if verbose:
        console.log(f"External connection {endpoint_name}")
    address = f"tcp://{host}:{port}"

    for connection in the_system.connections[app_name]:
        if connection.uid == endpoint_name:
            console.log(f"Duplicate external connection {endpoint_name} detected! Not adding to configuration!")
            return
    if len(topic) == 0:
        the_system.connections[app_name] += [conn.ConnectionId(uid=endpoint_name, service_type="kNetReceiver" if inout==Direction.IN else 'kNetSender', data_type="", uri=address)]
    else:
        the_system.connections[app_name] += [conn.ConnectionId(uid=endpoint_name, service_type="kPublisher" if inout==Direction.IN else 'kSubscriber', data_type="", uri=address, topics=topic)]

def make_network_connection(the_system, endpoint_name, in_apps, out_apps, verbose):
    if verbose:
        console.log(f"Connection {endpoint_name}, Network")
    if len(in_apps) > 1:
        raise ValueError(f"Connection with name {endpoint_name} has multiple receivers, which is unsupported for a network connection!")
    the_system.app_connections[endpoint_name] = AppConnection(bind_apps=in_apps, connect_apps=out_apps)

    port = the_system.next_unassigned_port()
    address = f'tcp://{{host_{in_apps[0]}}}:{port}'
    the_system.connections[in_apps[0]] += [conn.ConnectionId(uid=endpoint_name, service_type="kNetReceiver", data_type="", uri=address)]
    for app in set(out_apps):
        the_system.connections[app] += [conn.ConnectionId(uid=endpoint_name, service_type="kNetSender", data_type="", uri=address)]

def make_system_connections(the_system, verbose=False):
    """Given a system with defined apps and endpoints, create the
    set of connections that satisfy the endpoints.

    If an endpoint's ID only exists for one application, a queue will
    be used.

    If an endpoint's ID exists for multiple applications, a network connection
    will be created, unless the inputs and outputs are exactly paired between
    those applications. (Each application in the set of applications that has
    that endpoint has exactly one input and one output with that endpoint name)

    If a queue connection has a single producer and single consumer, it will use FollySPSC,
    otherwise FollyMPMC will be used.


    """

    external_uids = set()
    uids = []
    endpoint_map = defaultdict(list)
    topic_map = defaultdict(list)

    for app in the_system.apps:
      the_system.connections[app] = []
      for queue in the_system.apps[app].modulegraph.queues:
            make_queue_connection(the_system, app, queue.name, queue.push_modules, queue.pop_modules, queue.size, verbose)
      for external_conn in the_system.apps[app].modulegraph.external_connections:
            make_external_connection(the_system, external_conn.external_name, app, external_conn.host, external_conn.port, external_conn.topic, external_conn.direction, verbose)
            external_uids.add(external_conn.external_name)
      for endpoint in the_system.apps[app].modulegraph.endpoints:
        uids.append(endpoint.external_name)
        if len(endpoint.topic) == 0:
            if verbose:
                console.log(f"Adding endpoint {endpoint.external_name}, app {app}, direction {endpoint.direction}")
            endpoint_map[endpoint.external_name] += [{"app": app, "endpoint": endpoint}]
        else:
            if verbose:
                console.log(f"Getting topics for endpoint {endpoint.external_name}, app {app}, direction {endpoint.direction}")
            for topic in endpoint.topic:
                topic_map[topic] += [{"app": app, "endpoint": endpoint}]

    for external_uid in external_uids:
        if external_uid in topic_map.keys():
            raise ValueError(f"Name {external_uid} is both a topic and an external connection name")
        if external_uid in uids:
            raise ValueError(f"Name {external_uid} is both an endpoint name and an external connection name")

    for topic in topic_map.keys():
        if topic in uids:
            raise ValueError(f"Name {topic} is both an endpoint external name and a topic name")

    for endpoint_name,endpoints in endpoint_map.items():
        if verbose:
            console.log(f"Processing {endpoint_name} with defined endpoints {endpoints}")
        first_app = endpoints[0]["app"]
        in_apps = []
        out_apps = []
        size = 0
        for endpoint in endpoints:
            direction = endpoint['endpoint'].direction
            if direction == Direction.IN:
                in_apps += [endpoint["app"]]
            else:
                out_apps += [endpoint["app"]]
            if endpoint['endpoint'].size_hint > size:
                size = endpoint['endpoint'].size_hint

        if len(in_apps) == 0:
            raise ValueError(f"Connection with name {endpoint_name} has no consumers!")
        if len(out_apps) == 0:
            raise ValueError(f"Connection with name {endpoint_name} has no producers!")

        if all(first_app == elem["app"] for elem in endpoints):
            make_queue_connection(the_system, first_app, endpoint_name, in_apps, out_apps, size, verbose)
        elif len(in_apps) == len(out_apps):
            paired_exactly = False
            if len(set(in_apps)) == len(in_apps) and len(set(out_apps)) == len(out_apps):
                paired_exactly = True
                for in_app in in_apps:
                    if(out_apps.count(in_app) != 1):
                        paired_exactly = False
                        break

                if paired_exactly:
                    for in_app in in_apps:
                        for app_endpoint in the_system.apps[in_app].modulegraph.endpoints:
                            if app_endpoint.external_name == endpoint_name:
                                app_endpoint.external_name = f"{in_app}.{endpoint_name}"
                        make_queue_connection(the_system,in_app, f"{in_app}.{endpoint_name}", [in_app], [in_app], size, verbose)

            if paired_exactly == False:
                make_network_connection(the_system, endpoint_name, in_apps, out_apps, verbose)

        else:
            make_network_connection(the_system, endpoint_name, in_apps, out_apps, verbose)

    pubsub_connectionids = {}
    for topic, endpoints in topic_map.items():
        if verbose:
            console.log(f"Processing {topic} with defined endpoints {endpoints}")

        publishers = []
        subscribers = [] # Only really care about the topics from here
        topic_connectionids = []

        for endpoint in endpoints:
            direction = endpoint['endpoint'].direction
            if direction == Direction.IN:
                subscribers += [endpoint["app"]]
            else:
                publishers += [endpoint["app"]]
                if endpoint['endpoint'].external_name not in pubsub_connectionids:
                    port = the_system.next_unassigned_port()
                    address = f'tcp://{{host_{endpoint["app"]}}}:{port}'
                    pubsub_connectionids[endpoint['endpoint'].external_name] = conn.ConnectionId(uid=endpoint['endpoint'].external_name, service_type="kPublisher", data_type="", uri=address, topics=endpoint['endpoint'].topic)
                the_system.connections[endpoint['app']] += [pubsub_connectionids[endpoint['endpoint'].external_name]]
                topic_connectionids += [pubsub_connectionids[endpoint['endpoint'].external_name]]

        if len(subscribers) == 0:
            raise ValueError(f"Topic {topic} has no subscribers!")
        if len(publishers) == 0:
            raise ValueError(f"Topic {topic} has no publishers!")

        the_system.app_connections[topic] = AppConnection(bind_apps=publishers, connect_apps=subscribers)
        for subscriber in subscribers:
            topic_connectionids_sub = cp.deepcopy(topic_connectionids)
            for topic_connectionid_sub in topic_connectionids_sub:
                topic_connectionid_sub.service_type = 'kSubscriber'

            temp_list = the_system.connections[subscriber] + topic_connectionids_sub
            the_system.connections[subscriber] = list(set(temp_list))




def make_app_command_data(system, app, appkey, verbose=False):
    """Given an App instance, create the 'command data' suitable for
    feeding to nanorc. The needed queues are inferred from from
    connections between modules, as are the start and stop order of the
    modules

    TODO: This should probably be split up into separate stages of
    inferring/creating the queues (which can be part of validation)
    and actually making the command data objects for nanorc.

    """

    if verbose:
        console.log(f"Making app command data for {app.name}")


    command_data = {}

    if len(system.connections) == 0:
        make_system_connections(system, verbose)

    module_deps = make_module_deps(app, system.connections[appkey], verbose)
    if verbose:
        console.log(f"inter-module dependencies are: {module_deps}")

    stop_order = list(nx.algorithms.dag.topological_sort(module_deps))
    start_order = stop_order[::-1]

    if verbose:
        console.log(f"Inferred module start order is {start_order}")
        console.log(f"Inferred module stop order is {stop_order}")

    app_connrefs = defaultdict(list)
    for endpoint in app.modulegraph.endpoints:
        if endpoint.internal_name is None:
            continue
        module, name = endpoint.internal_name.split(".")
        if verbose:
            console.log(f"module, name= {module}, {name}, endpoint.external_name={endpoint.external_name}, endpoint.direction={endpoint.direction}")
        app_connrefs[module] += [conn.ConnectionRef(name=name, uid=endpoint.external_name, dir= "kInput" if endpoint.direction == Direction.IN else "kOutput")]

    for external_conn in app.modulegraph.external_connections:
        if external_conn.internal_name is None:
            continue
        module, name = external_conn.internal_name.split(".")
        if verbose:
            console.log(f"module, name= {module}, {name}, external_conn.external_name={external_conn.external_name}, external_conn.direction={external_conn.direction}")
        app_connrefs[module] += [conn.ConnectionRef(name=name, uid=external_conn.external_name, dir= "kInput" if external_conn.direction == Direction.IN else "kOutput")]

    for queue in app.modulegraph.queues:
        queue_uid = queue.name
        for push_mod in queue.push_modules:
            module, name = push_mod.split(".", maxsplit=1)
            app_connrefs[module] += [conn.ConnectionRef(name=name, uid=queue_uid, dir="kOutput")]
        for pop_mod in queue.pop_modules:
            module, name = pop_mod.split(".", maxsplit=1)
            app_connrefs[module] += [conn.ConnectionRef(name=name, uid=queue_uid, dir="kInput")]

    if verbose:
        console.log(f"Creating mod_specs for {[ (mod.name, mod.plugin) for mod in app.modulegraph.modules ]}")
    mod_specs = [ mspec(mod.name, mod.plugin, app_connrefs[mod.name]) for mod in app.modulegraph.modules ]

    # Fill in the "standard" command entries in the command_data structure

    command_data['init'] = appfwk.Init(modules=mod_specs, connections=system.connections[appkey])

    # TODO: Conf ordering
    command_data['conf'] = acmd([
        (mod.name, mod.conf) for mod in app.modulegraph.modules
    ])

    startpars = rccmd.StartParams(run=1, disable_data_storage=False)
    resumepars = rccmd.ResumeParams()

    add_one_command_data(command_data, "start",   startpars,  app, start_order)
    add_one_command_data(command_data, "stop",    None,       app, stop_order)
    add_one_command_data(command_data, "scrap",   None,       app, stop_order)
    add_one_command_data(command_data, "resume",  resumepars, app, start_order)
    add_one_command_data(command_data, "pause",   None,       app, stop_order)

    # TODO: handle modules' `extra_commands`, including "record"

    return command_data

def geoid_raw_str(geoid):
    """Get a string representation of a GeoID suitable for using in queue names"""
    return f"geoid{geoid.system}_{geoid.region}_{geoid.element}"

def data_request_endpoint_name(producer):
    return f"data_request_{geoid_raw_str(producer.geoid)}"

def resolve_endpoint(app, external_name, inout, verbose=False):
    """
    Resolve an `external` endpoint name to the corresponding internal "module.sinksource"
    """
    if external_name in app.modulegraph.endpoints:
        e=app.modulegraph.endpoints[external_name]
        if e.direction==inout:
            if verbose:
                console.log(f"Endpoint {external_name} resolves to {e.internal_name}")
            return e.internal_name
        else:
            raise KeyError(f"Endpoint {external_name} has direction {e.direction}, but requested direction was {inout}")
    else:
        raise KeyError(f"Endpoint {external_name} not found")

def make_unique_name(base, module_list):
    module_names = [ mod.name for mod in module_list ]
    suffix=0
    while f"{base}_{suffix}" in module_names:
        suffix+=1
    assert f"{base}_{suffix}" not in module_names

    return f"{base}_{suffix}"

def generate_boot(apps: list, ers_settings=None, info_svc_uri="file://info_${APP_ID}_${APP_PORT}.json",
                  disable_trace=False, use_kafka=False, verbose=False, extra_env_vars=dict()) -> dict:
    """Generate the dictionary that will become the boot.json file"""

    if ers_settings is None:
        ers_settings={
            "INFO":    "erstrace,throttle,lstdout",
            "WARNING": "erstrace,throttle,lstdout",
            "ERROR":   "erstrace,throttle,lstdout",
            "FATAL":   "erstrace,lstdout",
        }

    daq_app_specs = {
        "daq_application_ups" : {
            "comment": "Application profile based on a full dbt runtime environment",
            "env": {
                "DBT_AREA_ROOT": "getenv",
                "TRACE_FILE": "getenv:/tmp/trace_buffer_${HOSTNAME}_${USER}",
            },
            "cmd": ["CMD_FAC=rest://localhost:${APP_PORT}",
                    "INFO_SVC=" + info_svc_uri,
                    "cd ${DBT_AREA_ROOT}",
                    "source dbt-env.sh",
                    "dbt-workarea-env",
                    "cd ${APP_WD}",
                    "daq_application --name ${APP_NAME} -c ${CMD_FAC} -i ${INFO_SVC}"]
        },
        "daq_application" : {
            "comment": "Application profile using  PATH variables (lower start time)",
            "env":{
                "CET_PLUGIN_PATH": "getenv",
                "DETCHANNELMAPS_SHARE": "getenv",
                "DUNEDAQ_SHARE_PATH": "getenv",
                "TIMING_SHARE": "getenv",
                "LD_LIBRARY_PATH": "getenv",
                "PATH": "getenv",
                # "READOUT_SHARE": "getenv",
                "TRACE_FILE": "getenv:/tmp/trace_buffer_${HOSTNAME}_${USER}",
            },
            "cmd": ["CMD_FAC=rest://localhost:${APP_PORT}",
                    "INFO_SVC=" + info_svc_uri,
                    "cd ${APP_WD}",
                    "daq_application --name ${APP_NAME} -c ${CMD_FAC} -i ${INFO_SVC}"]
        }
    }

    first_port = 3333
    ports = {}
    for i, name in enumerate(apps.keys()):
        ports[name] = first_port + i

    boot = {
        "env": {
            "DUNEDAQ_ERS_VERBOSITY_LEVEL": "getenv:1",
            "DUNEDAQ_ERS_INFO": ers_settings["INFO"],
            "DUNEDAQ_ERS_WARNING": ers_settings["WARNING"],
            "DUNEDAQ_ERS_ERROR": ers_settings["ERROR"],
            "DUNEDAQ_ERS_FATAL": ers_settings["FATAL"],
            "DUNEDAQ_ERS_DEBUG_LEVEL": "getenv_ifset",
        },
        "apps": {
            name: {
                "exec": "daq_application",
                "host": f"host_{name}",
                "port": ports[name]
            }
            for name, app in apps.items()
        },
        "hosts": {
            f"host_{name}": app.host
            for name, app in apps.items()
        },
        "response_listener": {
            "port": 56789
        },
        "exec": daq_app_specs
    }

    boot["exec"]["daq_application"]["env"].update(extra_env_vars)
    boot["exec"]["daq_application_ups"]["env"].update(extra_env_vars)

    if disable_trace:
        del boot["exec"]["daq_application"]["env"]["TRACE_FILE"]
        del boot["exec"]["daq_application_ups"]["env"]["TRACE_FILE"]

    if use_kafka:
        boot["env"]["DUNEDAQ_ERS_STREAM_LIBS"] = "erskafka"

    if verbose:
        console.log("Boot data")
        console.log(boot)

    return boot


cmd_set = ["init", "conf", "start", "stop", "pause", "resume", "scrap"]


def make_app_json(app_name, app_command_data, data_dir, verbose=False):
    """Make the json files for a single application"""
    if verbose:
        console.log(f"make_app_json for app {app_name}")
    for c in cmd_set:
        with open(f'{join(data_dir, app_name)}_{c}.json', 'w') as f:
            json.dump(app_command_data[c].pod(), f, indent=4, sort_keys=True)

def make_system_command_datas(the_system, verbose=False):
    """Generate the dictionary of commands and their data for the entire system"""

    if the_system.app_start_order is None:
        app_deps = make_app_deps(the_system, verbose)
        the_system.app_start_order = list(nx.algorithms.dag.topological_sort(app_deps))

    system_command_datas=dict()

    for c in cmd_set:
        console.log(f"Generating system {c} command")
        cfg = {
            "apps": {app_name: f'data/{app_name}_{c}' for app_name in the_system.apps.keys()}
        }
        if c == 'start':
            cfg['order'] = the_system.app_start_order
        elif c == 'stop':
            cfg['order'] = the_system.app_start_order[::-1]

        system_command_datas[c]=cfg

        if verbose:
            console.log(cfg)

    console.log(f"Generating boot json file")
    system_command_datas['boot'] = generate_boot(the_system.apps, verbose=verbose)

    return system_command_datas

def write_json_files(app_command_datas, system_command_datas, json_dir, verbose=False):
    """Write the per-application and whole-system command data as json files in `json_dir`
    """

    console.rule("JSON file creation")

    if exists(json_dir):
        raise RuntimeError(f"Directory {json_dir} already exists")

    data_dir = join(json_dir, 'data')
    os.makedirs(data_dir)

    # Apps
    for app_name, command_data in app_command_datas.items():
        make_app_json(app_name, command_data, data_dir, verbose)

    # System commands
    for cmd, cfg in system_command_datas.items():
        with open(join(json_dir, f'{cmd}.json'), 'w') as f:
            json.dump(cfg, f, indent=4, sort_keys=True)

    console.log(f"System configuration generated in directory '{json_dir}'")
