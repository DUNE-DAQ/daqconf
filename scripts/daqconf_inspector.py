#!/usr/bin/env python
from typing import Union
from rich import print
from rich.tree import Tree
from rich.table import Table

import click

import conffwk
import confmodel

import IPython

class DaqInspectorContext:
    pass

def make_segment_tree(cfg, segment, session: None, show_path: bool = False) -> Tree:
    '''
    Create segment branch of the configuration tree
    '''


    def enabled_to_emoji(enabled: Union[int, None]) -> str:
        match enabled:
            case 1:
                return ':white_check_mark:'
            case 0:
                return ':heavy_large_circle:' 
            case -1:
                return ':x:' 
            case _:
                return ':blue_circle:'
            
    def get_enabled(cfg, session, obj):
        if not obj.isDalType('Component'):
            return None

        enabled = not confmodel.component_disabled(cfg._obj, session.id, obj.id)
        if enabled:
            return enabled
        
        enabled -= (obj in session.disabled)
        return enabled
        

    path = f"[blue]{cfg.get_obj(segment.className(), segment.id).contained_in()}[/blue]" if show_path else ""
    enabled = get_enabled(cfg, session, segment) if session else None
    tree = Tree(f"{enabled_to_emoji(enabled)} [yellow]{segment.id}[/yellow] {path}")

    c = segment.controller
    path = f"[blue]{cfg.get_obj(c.className(), c.id).contained_in()}[/blue]" if show_path else ""
    ports = ', '.join([f'{svc.port}({svc.protocol})' for svc in c.exposes_service ])
    host = f"[medium_purple1]{c.runs_on.runs_on.id}[/medium_purple1]"
    tree.add(f"[cyan]controller[/cyan]: [green]{c.id}[/green][magenta]@{c.className()}[/magenta] on {host} [{ports}] {path}")

    if segment.applications:
        app_tree = tree.add(f"[cyan]applicationss[/cyan]")
        for a in segment.applications:
            if a is None:
                print(f"Detected None application in {segment.id}")
                continue

            path = f"[blue]{cfg.get_obj(a.className(), a.id).contained_in()}[/blue]" if show_path else ""
            ports = ', '.join([f'{svc.port}({svc.protocol})' for svc in c.exposes_service ])
            host = f"[medium_purple1]{a.runs_on.runs_on.id}[/medium_purple1]"
            enabled = get_enabled(cfg, session, a) if session else None

            app_tree.add(f"{enabled_to_emoji(enabled)} [green]{a.id}[/green][magenta]@{a.className()}[/magenta] on {host} [{ports}] {path}")

    if segment.segments:
        seg_tree = tree.add(f"[cyan]segments[/cyan]")
        for s in segment.segments:
            if s is None:
                print(f"Detected None segment in {segment.id}")
                continue
            seg_tree.add(make_segment_tree(cfg, s, session, show_path))

    return tree
    


@click.group()
@click.option('-i', '--interactive', is_flag=True, show_default=True, default=False)
@click.argument('config_file')
@click.pass_obj
def cli(obj, interactive, config_file):
    cfg = conffwk.Configuration(f"oksconflibs:{config_file}")
    obj.cfg = cfg

    if interactive:
        IPython.embed(colors="neutral")


@cli.command()
@click.option('-p', '--show-paths', is_flag=True, show_default=True, default=False)
@click.pass_obj
def show_sessions(obj, show_paths):
    """
    Display the list of sessions available in the configuration database and their internal structure
    """
    
    cfg = obj.cfg

    print("Sessions")
    sessions = cfg.get_objs("Session")
    for s in sessions:
        print(f" - '{s.UID()}' [blue]{s.contained_in()}[/blue]")

    print()

    for so in sessions:
        s = cfg.get_dal('Session', so.UID())
        tree = Tree(f"Session [yellow]{s.id}[/yellow]")

        tree.add(make_segment_tree(cfg, s.segment, s, show_paths))
        print(tree)
    print()


@cli.command()
@click.pass_obj
def list_classes(obj):
    """Prints the list of classes known to configuration"""
    from rich.highlighter import ReprHighlighter

    rh = ReprHighlighter()
    cfg = obj.cfg

    table = Table("Classes")
    table.add_column('Class', 'Objects')
    for k in sorted(cfg.classes()):
        table.add_row(k, rh(str([o.UID() for o in cfg.get_objs(k)])))
    print(table)

@cli.command()
@click.argument('klass')
@click.option('-v/-h','--vertical/--horizontal', "vtable", default=True)
@click.pass_obj
def show_class(obj, klass,vtable):
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

@cli.command()
@click.argument('klass')
@click.argument('id')
@click.pass_obj
def show_object_tree(obj, klass, id):
    from rich.highlighter import ReprHighlighter
    rh = ReprHighlighter()
    cfg = obj.cfg

    if klass not in cfg.classes():
        print('f[red]Class {klass} unknow to configuration[/red]')
        print(f'Known classes: {sorted(cfg.classes())}')
        raise SystemExit(-1)

    
    tokens = id.split('.')
    parent = tokens[0]
    children = tokens[1:]

    do = cfg.get_dal(klass, id)
    
    def make_obj_tree(dal_obj):
        tree = Tree(f"[green]{dal_obj.id}[/green][magenta]@{dal_obj.className()}[/magenta]")
        # attr_tree = tree.add('[yellow]attributes[/yellow]')
        attrs = cfg.attributes(dal_obj.className(), True)
        for a in attrs:
            tree.add(f"[cyan]{a}[/cyan] = {getattr(dal_obj, a)}")
        
        # rel_tree = tree.add('[yellow]relationships[/yellow]')
        rels = cfg.relations(dal_obj.className(), True)
        for rel, rinfo in rels.items():
            rel_val = getattr(dal_obj, rel)
            r_tree = tree.add(f"[yellow]{rel}[/yellow]@[magenta]{rinfo['type']}[/magenta] {('['+str(len(rel_val))+']' if isinstance(rel_val, list) else '')}")
            if not isinstance(rel_val,list):
                rel_val = [rel_val]
            for v in rel_val:
                if v is None:
                    continue
                r_tree.add(make_obj_tree(v))
        return tree


    tree = make_obj_tree(do, children)
    print(tree)


@cli.command()
@click.pass_obj
def check_detstreams(obj):

    cfg = obj.cfg
    print("DetectorStreams")

    IPython.embed(colors="neutral")

if __name__== "__main__":
    cli(obj=DaqInspectorContext())