from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Endpoint, Direction, GeoID, FragmentProducer, Queue
import networkx as nx

class ModuleGraph:
    """
    A set of modules and connections between them.

    modulegraph holds a dictionary of modules, with each module
    knowing its (outgoing) connections to other modules in the
    modulegraph.

    Connections to other modulegraphs are represented by
    `endpoints`. The endpoint's `external_name` is the "public" name
    of the connection, which other modulegraphs should use. The
    endpoint's `internal_name` specifies the particular module and
    sink/source name which the endpoint is connected to, which may be
    changed without affecting other applications.
    """

    def __init__(self, modules:[DAQModule]=None, endpoints=None, fragment_producers=None, queues=None):
        self.modules=modules if modules else []
        self.endpoints=endpoints if endpoints else []
        self.fragment_producers = fragment_producers if  fragment_producers else dict()
        self.queues = queues if queues else []

    def __repr__(self):
        return f"modulegraph(modules={self.modules}, endpoints={self.endpoints}, fragment_producers={self.fragment_producers})"

    def __rich_repr__(self):
        yield "modules", self.modules
        yield "endpoints", self.endpoints
        yield "fragment_producers", self.fragment_producers

    def set_from_dict(self, module_dict):
        self.modules=module_dict

    def digraph(self):
        deps = nx.DiGraph()
        modules_set = set()

        for module in self.modules:
            if module.name in modules_set:
                raise RuntimeError(f"Module {module.name} appears twice in the ModuleGraph")
            deps.add_node(module.name)
            modules_set.add(module.name)

        for queue in self.queues:
            for pop_mod in queue.pop_modules:
                for push_mod in queue.push_modules:
                    queue_start = push_mod.split(".")
                    if len(queue_start) != 2:
                        raise RuntimeError(f"Bad queue config!: {queue} output module must be specified as module.queue_name")
                    queue_end = pop_mod.split(".")
                    if len(queue_end) != 2:
                        raise RuntimeError(f"Bad queue config!: {queue} input module must be specified as module.queue_name")
                    deps.add_edge(queue_start[0], queue_end[0], label=queue.name)

        for endpoint in self.endpoints:
            if endpoint.internal_name is None:
                continue
            endpoint_internal_data = endpoint.internal_name.split(".")
            if len(endpoint_internal_data) != 2:
                raise RuntimeError(f'Bad endpoint!: {endpoint} internal_endpoint must be specified as module.queue_name')
            to_module = endpoint_internal_data[0]
            if to_module in modules_set:
                if endpoint.direction == Direction.IN:
                    deps.add_edge(endpoint.external_name, to_module, label=endpoint_internal_data[1])
                else:
                    deps.add_edge(to_module, endpoint.external_name, label=endpoint_internal_data[1])
                deps.nodes[endpoint.external_name]['color'] = 'red'
            else:
                raise RuntimeError(f"Bad endpoint {endpoint}: internal connection which doesn't connect to any module! Available modules: {modules_set}")

        # finally the fragment producers
        for producer in self.fragment_producers.values():
            producer_request_in = producer.requests_in.split(".")
            if len(producer_request_in) != 2:
                raise RuntimeError(f"Bad fragment producer {producer}: request_in must be specified as module.queue_name")

            if producer_request_in[0] in modules_set:
                deps.add_edge("TriggerRecordBuilder", producer_request_in[0], label='requests')
                deps.nodes["TriggerRecordBuilder"]['color'] = 'red'
            else:
                raise RuntimeError(f"Bad FragmentProducer {producer}: request_in doesn't connect to any module! Available modules: {modules_set}")

            producer_frag_out = producer.fragments_out.split(".")
            if len(producer_frag_out) != 2:
                raise RuntimeError(f"Bad fragment producer {producer}: fragments_out must be specified as module.queue_name")

            if producer_frag_out[0] in modules_set:
                deps.add_edge(producer_frag_out[0], "FragmentReceiver", label='fragments')
                deps.nodes["FragmentReceiver"]['color'] = 'orange'
            else:
                raise RuntimeError(f"Bad FragmentProducer {producer}: fragments_out doesn't connect to any module! Available modules: {modules_set}")

        return deps

    def get_module(self, name):
        for mod in self.modules:
            if mod.name == name:
                return mod
        return None

    def reset_module(self, name, new_module):
        for i,mod in enumerate(self.modules):
            if mod.name == name:
                self.modules[i] = new_module
                return
        raise RuntimeError(f'Module {name} not found!')

    def reset_module_conf(self, name, new_conf):
        """Replace the configuration object of the module `name` with the new object `conf`"""
        # It would be nice to just modify the `conf` attribute of the
        # DAQModule object directly, but moo-derived objects work in a funny
        # way (returning a copy of the attribute, not returning a
        # reference to it), which means we have to copy and replace the
        # whole module
        for i,mod in enumerate(self.modules):
            if mod.name == name:
                old_module = self.modules[i]
                new_module = DAQModule(name=name,
                                       plugin=old_module.plugin,
                                       conf=new_conf,
                                       connections=old_module.connections)
                self.modules[i] = new_module
                return
        raise RuntimeError(f'Module {name} not found!')

    def module_names(self):
        return [n.name for n in self.modules]

    def module_list(self):
        return self.modules

    def add_module(self, name, **kwargs):
        if self.get_module(name):
            raise RuntimeError(f"Module of name {name} already exists in this modulegraph")
        mod=DAQModule(name=name, **kwargs)
        self.modules.append(mod)
        return mod

    def add_endpoint(self, external_name, internal_name, inout, topic=[]):
        self.endpoints += [Endpoint(external_name, internal_name, inout, topic)]

    def connect_modules(self, push_addr, pop_addr, queue_name = "", size_hint = 10):
        queue_start = push_addr.split(".")
        queue_end = pop_addr.split(".")
        if len(queue_start) != 2 or len(queue_end) != 2 or queue_start[0] not in self.module_names() or queue_end[0] not in self.module_names():
            raise RuntimeError(f"connect_modules called with invalid parameters. push_addr and pop_addr must be of form <module>.<internal name>, and the module must already be in the module graph!")

        if queue_name == "":
            self.queues.append(Queue(push_addr, pop_addr, push_addr + "_to_" + pop_addr, size_hint))
        else:
            existing_queue = False
            for queue in self.queues:
                if queue.name == queue_name:
                    queue.add_module_link(push_addr, pop_addr)
                    existing_queue = True
            if not existing_queue:
                self.queues.append(Queue(push_addr, pop_addr, queue_name, size_hint))

    def endpoint_names(self, inout=None):
        if inout is not None:
            return [ e[0] for e in self.endpoints.items() if e[1].inout==inout ]
        return self.endpoints.keys()

    def add_fragment_producer(self, system, region, element, requests_in, fragments_out):
        geoid = GeoID(system, region, element)
        if geoid in self.fragment_producers:
            raise ValueError(f"There is already a fragment producer for GeoID {geoid}")
        # Can't set queue_name here, because the queue names need to be unique system-wide,
        # but we're inside a particular app here. Instead, we create the queue names in readout_gen.generate,
        # where all of the fragment producers are known
        queue_name = None
        self.fragment_producers[geoid] = FragmentProducer(geoid, requests_in, fragments_out, queue_name)

class App:
    """
    A single daq_application in a system, consisting of a modulegraph
    and a hostname on which to run
    """

    def __init__(self, modulegraph=None, host="localhost", name="__app"):
        if modulegraph:
            # hopefully that crashes if something is wrong!
            self.digraph = modulegraph.digraph()
            self.digraph.name = name

        self.modulegraph = modulegraph if modulegraph else ModuleGraph()
        self.host = host
        self.name = name

    def reset_graph(self):
        if self.modulegraph:
            self.digraph = self.modulegraph.digraph()

    def export(self, filename):
        if not self.digraph:
            raise RuntimeError("Cannot export a app which doesn't have a valid digraph")
        nx.drawing.nx_pydot.write_dot(self.digraph, filename)
