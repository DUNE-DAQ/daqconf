#!/usr/bin/env python

import daqconf.detreadoutmap as dromap


import click
import json
from rich import print
from rich.table import Table
from rich.console import Console

import click_shell

console = Console()

# ------------------------------------------------------------------------------
# Add -h as default help option
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
# ------------------------------------------------------------------------------

@click_shell.shell(prompt='dro> ', chain=True, context_settings=CONTEXT_SETTINGS)
@click.pass_obj
def cli(obj):
    pass


@cli.command('load', help="Load map from file")
@click.argument('path', type=click.Path(exists=True))
@click.option('--merge', is_flag=True, type=bool, default=False)
@click.pass_obj
def load(obj, path, merge):
    m = obj
    m.load(path, merge)

    console.print(m.as_table())

@cli.command('load-hw-map', help="Load map from a hardware map file")
@click.argument('path', type=click.Path(exists=True))
@click.pass_obj
def load_hw_map(obj, path):
    console.log("Loading HarwareMap libraries")
    from detchannelmaps._daq_detchannelmaps_py import HardwareMapService
    # Load configuration types
    import moo.otypes

    moo.otypes.load_types('detchannelmaps/hardwaremapservice.jsonnet')
    import dunedaq.detchannelmaps.hardwaremapservice as hwms

    console.log(f"Loading '{path}'")

    m = obj
    hwmap_svc = HardwareMapService(path)
    hw_map = hwmap_svc.get_hardware_map()
    for hw_info in hw_map.link_infos:
        m.add_srcid(
            hw_info.dro_source_id, 
            dromap.GeoID(
                    det_id=hw_info.det_id,
                    crate_id=hw_info.det_crate,
                    slot_id=hw_info.det_slot,
                    stream_id=hw_info.det_link,
                ), 
                'flx', 
                host=hw_info.dro_host,
                card=hw_info.dro_card,
                slr=hw_info.dro_slr,
                link=hw_info.dro_link,
            )

    console.print(m.as_table())

@cli.command('rm', help="Remove a stream")
@click.argument('src_id', type=int)
@click.pass_obj
def rm(obj, src_id):
    console.log(f"Removing {src_id}")
    m = obj
    m.remove_srcid(src_id)
    console.print(m.as_table())


@cli.command("add-flx", help="Add a felix stream")
@click.option('--force', type=bool, is_flag=True, default=False)
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
        
    console.log(f"Adding felix entry {src_id}")

    geo_args = {k.removeprefix('geo_'):v for k,v in kwargs.items() if k.startswith('geo_') and v is not None}
    flx_args = {k.removeprefix('flx_'):v for k,v in kwargs.items() if k.startswith('flx_') and v is not None}

    try:
        m.add_srcid(src_id, dromap.GeoID(**geo_args), 'flx', **flx_args )
    except ValueError:
        print(f"ERROR: {e}")
        raise click.ClickException(f"Failed to insert src {src_id}")
    print(m.as_table())

    
@cli.command("add-eth", help="Add an Ethernet stream")
@click.option('--force', type=bool, is_flag=True, default=False)
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


    console.log(f"Adding felix entry {src_id}")

    geo_args = {k.removeprefix('geo_'):v for k,v in kwargs.items() if k.startswith('geo_') and v is not None}
    eth_args = {k.removeprefix('eth_'):v for k,v in kwargs.items() if k.startswith('eth_') and v is not None}

    try:
        m.add_srcid(src_id, dromap.GeoID(**geo_args), 'eth', **eth_args )
    except ValueError as e:
        print(f"ERROR: {e}")
        raise click.ClickException(f"Failed to insert src {src_id}: {e}")
    print(m.as_table())


@cli.command("save", help="Save the map to json file")
@click.argument('path', type=click.Path())
@click.pass_obj
def save(obj, path):

    m = obj
    with open(path,"w") as f:
        json.dump(m.as_json(), f, indent=4)
    console.log(f"Map saved to '{path}'")
    

@cli.command("ipy", help="Start IPython")
@click.pass_obj
def ipy(obj):

    m = obj

    import IPython
    IPython.embed(colors="neutral")

if __name__ == "__main__":
    cli(obj=dromap.DetReadoutMapService())
