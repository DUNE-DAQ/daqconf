#!/usr/bin/env python

import daqconf.drolink_map as dromap


import click
import json
from rich import print
from rich.table import Table

@click.group(chain=True)
@click.pass_obj
def cli(obj):
    pass


@cli.command('load')
@click.argument('path', type=click.Path(exists=True))
@click.pass_obj
def load(obj, path):
    m = obj
    m.load(path)
    # print(m.get_by_type("flx"))

    print(m.as_table())


@cli.command('rm')
@click.argument('src_id', type=int)
@click.pass_obj
def rm(obj, src_id):
    print("Removing")
    m = obj
    m.remove_srcid(src_id)
    print(m.as_table())


@cli.command("add-flx")
@click.option('--force', type=bool, default=False)
@click.option('--src-id', type=int, default=None)
@click.option('--geo-det-id', type=int, default=0)
@click.option('--geo-crate-id', type=int, default=0)
@click.option('--geo-slot-id', type=int, default=0)
@click.option('--geo-stream-id', type=int, default=0)
@click.option('--flx-host')
@click.option('--flx-protocol')
@click.option('--flx-mode')
@click.option('--flx-card')
@click.option('--flx-slr')
@click.option('--flx-link')
@click.pass_obj
def add_flx(obj, force, src_id, **kwargs):
    m = obj

    if src_id is None:
        src_id = max(m.get())+1 if m.get() else 0
    elif src_id in m.get_src_ids() and force:
        m.remove_srcid(src_id)
        
    print(f"Adding felix entry {src_id}")

    geo_args = {k.removeprefix('geo_'):v for k,v in kwargs.items() if k.startswith('geo_') and v is not None}
    flx_args = {k.removeprefix('flx_'):v for k,v in kwargs.items() if k.startswith('flx_') and v is not None}

    m.add_srcid(src_id, dromap.GeoID(**geo_args), 'flx', **flx_args )
    print(m.as_table())

    
@cli.command("add-eth")
@click.option('--force', type=bool, default=False)
@click.option('--src-id', type=int, default=None)
@click.option('--geo-det-id', type=int, default=0)
@click.option('--geo-crate-id', type=int, default=0)
@click.option('--geo-slot-id', type=int, default=0)
@click.option('--geo-stream-id', type=int, default=0)
@click.option('--eth-protocol')
@click.option('--eth-mode')
@click.option('--eth-tx-host')
@click.option('--eth-tx-mac')
@click.option('--eth-tx-ip')
@click.option('--eth-rx-host')
@click.option('--eth-rx-mac')
@click.option('--eth-rx-ip')
@click.pass_obj
def add_eth(obj, force, src_id, **kwargs):
    m = obj


    if src_id is None:
        src_id = max(m.get())+1 if m.get() else 0
    elif src_id in m.get_src_ids() and force:
        m.remove_srcid(src_id)


    print(f"Adding felix entry {src_id}")

    geo_args = {k.removeprefix('geo_'):v for k,v in kwargs.items() if k.startswith('geo_') and v is not None}
    eth_args = {k.removeprefix('eth_'):v for k,v in kwargs.items() if k.startswith('eth_') and v is not None}

    m.add_srcid(src_id, dromap.GeoID(**geo_args), 'eth', **eth_args )
    print(m.as_table())


@cli.command("save")
@click.argument('path', type=click.Path())
@click.pass_obj
def save(obj, path):

    m = obj
    with open(path,"w") as f:
        json.dump(m.as_json(), f, indent=4)
    
if __name__ == "__main__":
    cli(obj=dromap.DROMapService())
