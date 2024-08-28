#!/usr/bin/env python
from rich import print
from rich.tree import Tree

import click

import conffwk

import IPython

class DaqInspectorContext:
    pass


def segment_tree(cfg, segment, show_path = False):

    path = f"[blue]{cfg.get_obj(segment.className(), segment.id).contained_in()}[/blue]" if show_path else ""
    tree = Tree(f"[yellow]{segment.id}[/yellow] {path}")
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
            app_tree.add(f"[green]{a.id}[/green][magenta]@{a.className()}[/magenta] on {host} [{ports}] {path}")
    if segment.segments:
        seg_tree = tree.add(f"[cyan]segments[/cyan]")
        for s in segment.segments:
            if s is None:
                print(f"Detected None segment in {segment.id}")
                continue
            seg_tree.add(segment_tree(cfg, s, show_path))

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

        tree.add(segment_tree(cfg, s.segment, show_paths))
        print(tree)
    print()

@cli.command()
@click.argument('klass')
@click.pass_obj
def show_class(obj, klass):

    cfg = obj.cfg
    
    if klass not in cfg.classes():
        print('f[red]Class {klass} unknow to configuration[/red]')
        print(f'Known classes: {cfg.classes()}')
        raise SystemExit(-1)
    print(f"Showing objects belonging to {klass}")

    attrs = cfg.attributes(klass)
    rels = cfg.relations(klass)


    for a in attrs:
        print(a)



    IPython.embed(colors="neutral")



@cli.command()
@click.pass_obj
def check_detstreams(obj):

    cfg = obj.cfg
    print("DetectorStreams")

    IPython.embed(colors="neutral")

if __name__== "__main__":
    cli(obj=DaqInspectorContext())