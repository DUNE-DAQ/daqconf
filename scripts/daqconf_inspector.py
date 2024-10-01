#!/usr/bin/env python
from typing import Union
from rich import print
from rich.tree import Tree
from rich.table import Table

import click

import conffwk

def start_ipython(loc):
    try:
        locals().update(loc)
        import IPython
        IPython.embed(colors="neutral")
    except ImportError:
        print(f"[red]IPython not available[/red]")

def is_enabled(cfg, session, obj):
    import confmodel

    """Helper function that returns the status of an object in a session"""
    if not obj.isDalType('Component'):
        return None

    enabled = not confmodel.component_disabled(cfg._obj, session.id, obj.id)
    if enabled:
        return enabled
    
    enabled -= (obj in session.disabled)
    return enabled

def get_attribute_info(o):
    return o.__schema__['attribute']

def get_relation_info(o):
    return o.__schema__['relation']

def get_attribute_list(o):
    return list(get_attribute_info(o))

def get_relation_list(o):
    return list(get_relation_info(o))

def get_superclass_list(o):
    return o.__schema__['superclass']

def get_subclass_list(o):
    return o.__schema__['subclass']

def compare_dal_obj(a, b):
    """Compare two dal objects by content"""

    # TODO: add a check on a and b being dal objects
    # There is no base class for dal objects in python, but dal objects have _shcema__objects.

    if a.className() != b.className():
        return False

    attrs = get_attribute_list(a)
    rels = get_relation_list(a)

    a_attrs = {x:getattr(a, x) for x in attrs}
    b_attrs = {x:getattr(b, x) for x in attrs}

    a_rels = {x:getattr(a, x) for x in rels}
    b_rels = {x:getattr(b, x) for x in rels}


    return (a_attrs == b_attrs) and (a_rels == b_rels)


#---------------
def find_related_dals(dal_obj, dal_group: set):


    rels = get_relation_list(dal_obj)

    rel_objs = set()
    for rel in rels:
        rel_val = getattr(dal_obj, rel)

        if rel_val is None:
            continue

        rel_objs.update(rel_val if isinstance(rel_val,list) else [rel_val])

    # Isolate relationship objects that are not in the dal_group yet
    new_rel_objs = rel_objs - dal_group

    # Safely add the new object to the group
    dal_group.update(rel_objs)
    for o in new_rel_objs:
        if o is None:
            continue

        find_related_dals(o, dal_group)
        
from collections.abc import Iterable
def find_duplicates( collection: Iterable ):
    """
    Find duplicated dal objects in a collection by based on objects attributes and relationships
    """
    
    n_items = len(collection)
    duplicates = set()
    for i in range(n_items):
        for j in range(i+1, n_items):
            if compare_dal_obj(collection[i], collection[j]):
                print(f"{i} {j} AAAAARGH")
                duplicates.add(collection[i])
                duplicates.add(collection[j])

    return duplicates

def enabled_to_emoji(enabled: Union[int, None]) -> str:
    """
    Convert enabled values [enabled, disabled, disabled-by-logic] into standard emojis
    """
    match enabled:
        case 1:
            return ':white_check_mark:'
        case 0:
            return ':heavy_large_circle:' 
        case -1:
            return ':x:' 
        case _:
            return ':blue_circle:'

def make_segment_tree(cfg, segment, session: None, show_path: bool = False) -> Tree:
    '''
    Create a segment branch of the session tree as a rich.Tree object
    ''' 

    path = f"[blue]{cfg.get_obj(segment.className(), segment.id).contained_in()}[/blue]" if show_path else ""
    enabled = is_enabled(cfg, session, segment) if session else None
    tree = Tree(f"{enabled_to_emoji(enabled)} [yellow]{segment.id}[/yellow] {path}")

    c = segment.controller
    path = f"[blue]{cfg.get_obj(c.className(), c.id).contained_in()}[/blue]" if show_path else ""
    ports = ', '.join([f'{svc.port}([orange1]{svc.protocol}[/orange1])' for svc in c.exposes_service ])
    host = f"[medium_purple1]{c.runs_on.runs_on.id}[/medium_purple1]"
    tree.add(f"[cyan]controller[/cyan]: [green]{c.id}[/green][magenta]@{c.className()}[/magenta] on {host} [{ports}] {path}")

    if segment.applications:
        app_tree = tree.add(f"[cyan]applicationss[/cyan]")
        for a in segment.applications:
            if a is None:
                print(f"Detected None application in {segment.id}")
                continue

            path = f"[blue]{cfg.get_obj(a.className(), a.id).contained_in()}[/blue]" if show_path else ""
            ports = ', '.join([f'{svc.port}([orange1]{svc.protocol}[/orange1])' for svc in c.exposes_service ])
            host = f"[medium_purple1]{a.runs_on.runs_on.id}[/medium_purple1]"
            enabled = is_enabled(cfg, session, a) if session else None

            app_tree.add(f"{enabled_to_emoji(enabled)} [green]{a.id}[/green][magenta]@{a.className()}[/magenta] on {host} [{ports}] {path}")

    if segment.segments:
        seg_tree = tree.add(f"[cyan]segments[/cyan]")
        for s in segment.segments:
            if s is None:
                print(f"Detected None segment in {segment.id}")
                continue
            seg_tree.add(make_segment_tree(cfg, s, session, show_path))

    return tree


def validate_oks_uid(ctx, param, value):
    """
    Helper function to validate OKS UID options or arguments accorinf to the format id@class
    """

    if isinstance(value, tuple):
        return value

    try:
        id, _, klass = value.partition("@")
        return str(id), str(klass)
    except ValueError:
        raise click.BadParameter("format must be '<id>@<class>'")

class DaqInspectorContext:
    pass

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--interactive', is_flag=True, show_default=True, default=False, help="Start an interactive IPython session after executing the commands")
@click.argument('config_file')
@click.pass_obj
def cli(obj, interactive, config_file):
    """
    A collection of helper commands to inspect dunedaq OKS databases and objects
    """
    cfg = conffwk.Configuration(f"oksconflibs:{config_file}")
    obj.cfg = cfg

    if interactive:
        start_ipython(locals())


@cli.command(short_help="Show sessions information")
@click.option('-p', '--show-file_paths', is_flag=True, show_default=True, default=False)
@click.pass_obj
def show_sessions(obj, show_file_paths):
    """
    Show high level information about the sessions from the configuration database
    """
    from rich.highlighter import ReprHighlighter
    rh = ReprHighlighter()
    
    cfg = obj.cfg

    print("Sessions")
    sessions = cfg.get_objs("Session")
    for s in sessions:
        print(f" - '{s.UID()}' [blue]{s.contained_in()}[/blue]")

    print()

    for so in sessions:

        grid = Table.grid("")
        

        s = cfg.get_dal('Session', so.UID())
        tree = Tree(f"[yellow]{s.id}[/yellow]")
        infra_tree = tree.add('[yellow]infra-apps[/yellow]')
        for a in s.infrastructure_applications:
            infra_tree.add(a.id)

        tree.add(make_segment_tree(cfg, s.segment, s, show_file_paths))

        t = Table("body", title='Session Tree', show_header=False, expand=True)
        t.add_row(tree)
        grid.add_row(t)
        
        # print(t)
        
        session_objs = set()
        find_related_dals(s, session_objs)

        # Find all objects in the top segment (exclude disabled, variables and infra in the resource count))
        segment_objs = set()
        find_related_dals(s.segment, segment_objs)        
        res = [o for o in segment_objs if 'ResourceBase' in o.oksTypes()]



        t = Table(title=s.id, show_header=False, expand=True)
        t.add_column('name')
        t.add_column('value')

        t.add_row('Objects', rh(str(len(session_objs))))
        t.add_row('Disabled mask', rh(str([ i.id for i in s.disabled])))
        t.add_row('Disabled resources', rh(str([ r.id for r in res if is_enabled(cfg, s, r) != 1])))
        # print(t)
        grid.add_row(t)

        disabled_not_in_session = set(s.disabled)-segment_objs
        if disabled_not_in_session:
            print(f"⚠️ {sorted(disabled_not_in_session)}")

        if s.environment:
            # print(s.environment)
            env_objs = set()
            for e in s.environment:
                env_objs.add(e)
                find_related_dals(e, env_objs)

            env_var = sorted(env_objs, key=lambda x: x.id)

            t = Table(title="Environment", show_header=False,  expand=True)
            t.add_column('name')
            t.add_column('value')
            for e in env_var:
                if 'Variable' not in e.oksTypes():
                    continue
                t.add_row(e.id, e.value)
            # print(t)
            grid.add_row(t)
            print(grid)
            print()


@cli.command(short_help="List known classes and objects for each class")
@click.pass_obj
@click.option('-d', "--show-derived-objects-as-parents", "show_derived", is_flag=True, default=False, help="Include derived objects in parent class listing")
def list_classes(obj, show_derived):
    """
    Prints on screen the list of classes known to the schema,
    together with the ids of objects belonging to that class.
    """
    from rich.highlighter import ReprHighlighter

    rh = ReprHighlighter()
    cfg = obj.cfg

    table = Table("Classes")
    table.add_column('Class', 'Objects')
    for k in sorted(cfg.classes()):
        table.add_row(k, rh(str([o.UID() for o in cfg.get_objs(k) if (o.class_name() == k or show_derived)])))
    print(table)

@cli.command(short_help="Show properties of objects forma class")
@click.argument('klass')
@click.option('-v/-h','--vertical/--horizontal', "vtable", default=True, help="Vertical or horizontal orientation")
@click.pass_obj
def show_obj_of_class(obj, klass, vtable):
    """
    Show attributes and relationships of all objects in the database belonging to KLASS
    """

    from rich.highlighter import ReprHighlighter

    rh = ReprHighlighter()
 
    cfg = obj.cfg
    
    if klass not in cfg.classes():
        print('f[red]Class {klass} unknow to configuration[/red]')
        print(f'Known classes: {sorted(cfg.classes())}')
        raise SystemExit(-1)

    attrs = cfg.attributes(klass, True)
    rels = cfg.relations(klass, True)

    dals = cfg.get_dals(klass)

    if vtable:
        table = Table(title=klass)
        table.add_column('Member', style="cyan")

        for do in dals:
            table.add_column(do.id)

        for a in attrs:
            table.add_row(*([a]+[rh(str(getattr(do,a))) for do in dals]))

        for r in rels:
            rel_vals = [getattr(do,r) for do in dals]
            rel_strs = []
            for rv in rel_vals:
                if isinstance(rv,list):
                    rel_strs += [rh(str([getattr(v,'id', 'None') for v in rv]))]
                else:
                    rel_strs += [rh(getattr(rv,'id', 'None'))]
            table.add_row(*([f"{r} ([yellow]{rels[r]['type']}[/yellow])"]+rel_strs))
    else:

        table = Table(title=klass)
        table.add_column('id', style="cyan")
        for a in attrs:
            table.add_column(a)

        for r,ri in rels.items():
            table.add_column(f"{r} ([yellow]{rels[r]['type']}[/yellow])")
        
        for do in dals:
            attr_vals = [rh(str(getattr(do,a))) for a in attrs]
            rel_vals = [getattr(do,r) for r in rels]
            rel_strs = []
            for rv in rel_vals:
                if isinstance(rv,list):
                    rel_strs += [rh(str([getattr(v,'id', 'None') for v in rv]))]
                else:
                    rel_strs += [rh(getattr(rv,'id', 'None'))]
            table.add_row(*([do.id]+attr_vals+rel_strs))

    print(table)

@cli.command(short_help="Show relationship tree")
@click.argument('uid', type=click.UNPROCESSED, callback=validate_oks_uid, default=None)
@click.option('+a/-a','--show-attributes/--hide-attributes', "show_attrs", default=True, help="Show/Hide attributes")
@click.option('-l','--level', "level", type=int, default=None, help="Recursion level in the object tree")
@click.option('-p','--path', "path", default=None, help="Path within the object relationships to visualise")
@click.pass_obj
def show_object_tree(obj, uid, show_attrs, path, level):
    """
    Show the relationship tree of the OKS object with identifier UID.

    The format of UID is <object name>@<class>
    """
    id, klass = uid

    from rich.highlighter import ReprHighlighter
    rh = ReprHighlighter()
    cfg = obj.cfg

    if klass not in cfg.classes():
        print('f[red]Class {klass} unknow to configuration[/red]')
        print(f'Known classes: {sorted(cfg.classes())}')
        raise SystemExit(-1)

    
    path = path.split('.') if path is not None else []

    try:
        do = cfg.get_dal(klass, id)
    except RuntimeError as e:
        raise click.BadArgumentUsage(f"Object '{id}' does not exist")



    def make_obj_tree(dal_obj, show_attrs, path=[], level=None):
        tree = Tree(f"[green]{dal_obj.id}[/green][magenta]@{dal_obj.className()}[/magenta]")
        if level == 0:
            return tree

        attrs = cfg.attributes(dal_obj.className(), True)
        rels = cfg.relations(dal_obj.className(), True)

        rel_sel = None
        if path:
            if path[0] not in rels:
                raise click.BadArgumentUsage(f"Object '{path[0]}' does not exist in {dal_obj.id}")
            else:
                rel_sel = path[0]
                path = path[1:]

        if show_attrs:
            for a in attrs:
                tree.add(f"[cyan]{a}[/cyan] = {getattr(dal_obj, a)}")
            
        # rels = cfg.relations(dal_obj.className(), True)
        rels = get_relation_info(dal_obj)
        for rel, rinfo in rels.items():
            # Filter on relationship name if path is specified
            if rel_sel and rel != rel_sel:  
                continue

            rel_val = getattr(dal_obj, rel)
            r_tree = tree.add(f"[yellow]{rel}[/yellow]@[magenta]{rinfo['type']}[/magenta] {('['+str(len(rel_val))+']' if isinstance(rel_val, list) else '')}")

            if not isinstance(rel_val,list):
                rel_val = [rel_val]

            for val in rel_val:
                if path and val.id != path[0]:
                    continue
                if val is None:
                    continue
                r_tree.add(make_obj_tree(val, show_attrs, path[1:], level-1 if level is not None else None))
        return tree


    tree = make_obj_tree(do, show_attrs, path, level)
    print(tree)

        
# @cli.command()
# @click.argument('uid', type=click.UNPROCESSED, callback=validate_oks_uid, default=None)
# @click.pass_obj
# def test_find_relations(obj, uid):

#     cfg = obj.cfg
#     id, klass = uid


#     if klass not in cfg.classes():
#         print(f'[red]Class {klass} unknow to configuration[/red]')
#         print(f'Known classes: {sorted(cfg.classes())}')
#         raise SystemExit(-1)

#     try:
#         dal_obj = cfg.get_dal(klass, id)
#     except RuntimeError as e:
#         raise click.BadArgumentUsage(f"Object '{id}' does not exist")
    
#     print(dal_obj)
    
#     grp = set()
#     find_related_dals(dal_obj, grp)

#     print(f"Found {len(grp)} objects related to {id}@{klass}")
#     # print(grp)
#     IPython.embed(colors="neutral")


@cli.command(short_help="Validate detector strams in the database")
@click.pass_obj
def validate_detstreams(obj):
    """
    Validates detector datastreams in a database.

    The command checks the collection of all detastreans in the database for uiniqueness.
    It also checks that all geo_ids references by detecor streams are unique.
    """
    from rich.highlighter import ReprHighlighter
    rh = ReprHighlighter()
    cfg = obj.cfg


    klass = 'DetectorStream'
    ds_attrs = cfg.attributes(klass, True)
    ds_rels = cfg.relations(klass, True)

    if list(ds_rels) != ['geo_id']:
        raise click.ClickException(f"Unexpected relationships found in DetectorStream {ds_rels}")


    gid_attrs = cfg.attributes("GeoId", True)
    gid_rels = cfg.relations("GeoId", True)

    if gid_rels:
        raise click.ClickException("Geoids are not expected to have relationships")


    streams = cfg.get_dals(klass)
    streams = sorted(streams, key=lambda x: x.source_id)


    table = Table(title='DetectorStreams')
    table.add_column('id')
    table.add_column('status')

    for a in ds_attrs:
        table.add_column(a)

    table.add_column('geo_id.id')

    for a in gid_attrs:
        table.add_column(f"{a}")


    for strm in streams:
        enabled_marker = ':blue_circle:'
        
        ds_attr_vals = [rh(str(getattr(strm,a))) for a in ds_attrs]
        gid_attr_vals = [rh(str(getattr(strm.geo_id,a))) for a in gid_attrs]

        table.add_row(*([strm.id, enabled_marker]+ds_attr_vals+[strm.geo_id.id]+gid_attr_vals))

    print(table)

    # Check for duplicate strm
    strm_duplicates = find_duplicates(streams)

    if strm_duplicates:
        print(f"[yellow]WARNING: found duplicates in detector streams {strm_duplicates}[/yellow]")
    else:
        print(f"[green]:white_check_mark: No duplicates among detector streams[/green]")


    gid_duplicates = find_duplicates([strm.geo_id for strm in streams])

    if gid_duplicates:
        print(f"[yellow]WARNING: found duplicates in geo ids {strm_duplicates}[/yellow]")
    else:
        print(f"[green]:white_check_mark: No duplicates among geo ids[/green]")



    # start_ipython(locals())

if __name__== "__main__":
    cli(obj=DaqInspectorContext())