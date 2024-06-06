import conffwk
import os
import json
import sys

def dro_json_to_oks(jsonfile, oksfile, source_id_offset, nomap, lcores):
    """Simple script to convert a JSON readout map file to an OKS file."""

    group_name = os.path.basename(jsonfile).removesuffix(".json")
    if oksfile == "":
        oksfile = group_name + ".data.xml"

    print(
        f"Converting RO map from {jsonfile} to OKS in {oksfile} offsetting source_ids by {source_id_offset}"
    )

    with open(jsonfile) as f:
        jsonmap = json.loads(f.read())
        f.close()

    schemafiles = [
        "schema/coredal/dunedaq.schema.xml",
        "schema/appdal/application.schema.xml",
        "schema/appdal/fdmodules.schema.xml",
    ]
    dal = conffwk.dal.module("generated", schemafiles[2])
    db = conffwk.Configuration("oksconflibs")
    db.create_db(oksfile, schemafiles)

    groups = []
    eth_streams = []
    flx_streams = []
    last_eth_pars = None
    last_felix_pars = None
    last_hermes_id = None
    eth_streams_found = False
    flx_streams_found = False
    nic_dals = {}
    stream_dals = {}
    rx_queue = 0
    for entry in jsonmap:
        source_id = entry["src_id"] + source_id_offset
        geo_id = entry["geo_id"]
        geo_dal = dal.GeoId(f"geoId-{source_id}",
                            detector_id=geo_id["det_id"],
                            crate_id=geo_id["crate_id"],
                            slot_id=geo_id["slot_id"],
                            stream_id=geo_id["stream_id"]
                            )
        db.update_dal(geo_dal)

        if entry["kind"] == "eth":
            eth_source_id = source_id
            if not eth_streams_found:
                eth_streams_found = True
                nic_config_dal = dal.NICInterfaceConfiguration(
                    f"nicConfig-{group_name}"
                )
                db.update_dal(nic_config_dal)
            pars = entry["parameters"]
            if last_eth_pars != None:
                #print(f"streams in nic {pars['rx_mac']} = {len(streams)}")
                if pars["rx_mac"] != last_eth_pars["rx_mac"]:
                    nic_name = f"nic-{last_eth_pars['rx_host']}"
                    print(f"New nic adding nic {last_eth_pars['rx_mac']} with id {nic_name}")
                    nic_dal = dal.NICInterface(
                        nic_name,
                        rx_hostname=last_eth_pars["rx_host"],
                        rx_mac=last_eth_pars["rx_mac"],
                        rx_ip=last_eth_pars["rx_ip"],
                        rx_iface=last_eth_pars["rx_iface"],
                        rx_pcie_addr=last_eth_pars["rx_pcie_dev"],
                        contains=eth_streams,
                        configuration=nic_config_dal
                    )
                    db.update_dal(nic_dal)
                    nic_dals[nic_name] = nic_dal
                    rogroup_dal = dal.ReadoutGroup(
                        f"group-{last_eth_source_id}",
                        contains=[nic_dal]
                    )
                    db.update_dal(rogroup_dal)
                    groups.append(rogroup_dal)
                    eth_streams = []
                    rx_queue = 0
            if pars != last_eth_pars:
                # Only create a new dal object if the parameters are different to the last one
                stream_pars = dal.EthStreamParameters(
                    f"pars-{source_id}",
                    protocol = pars["protocol"],
                    mode = pars["mode"],
                    tx_hostname = pars["tx_host"],
                    tx_mac = pars["tx_mac"],
                    tx_ip = pars["tx_ip"],
                    lcore = lcores[rx_queue%len(lcores)],
                    rx_queue = rx_queue
                )
                db.update_dal(stream_pars)
                rx_queue = rx_queue + 1
                last_eth_pars = pars
                last_eth_source_id = source_id
        elif entry["kind"] == "flx":
            flx_source_id = source_id
            flx_streams_found = True
            pars = entry["parameters"]
            if not last_felix_pars == None:
                if (
                    pars["card"] != last_felix_pars["card"]
                    or pars["slr"] != last_felix_pars["slr"]
                ):
                    print(
                        f'Adding FelixInterface felix-{last_felix_source_id} slr={last_felix_pars["slr"]}'
                    )
                    felix_dal = dal.FelixInterface(
                        f"felix-{last_felix_source_id}",
                        card=last_felix_pars["card"],
                        slr=last_felix_pars["slr"],
                        contains=flx_streams
                    )
                    db.update_dal(felix_dal)
                    rogroup_dal = dal.ReadoutGroup(
                        f"group-{last_felix_source_id}",
                        contains=[felix_dal]
                    )
                    db.update_dal(rogroup_dal)
                    groups.append(rogroup_dal)
                    flx_streams = []
            stream_pars = dal.FelixStreamParameters(
                f"flxpars-{source_id}",
                protocol=pars["protocol"],
                mode=pars["mode"],
                link=pars["link"]
            )
            db.update_dal(stream_pars)
            last_felix_pars = pars
            last_felix_source_id = source_id
        else:
            raise RuntimeError(f'Unknown kind of readout {entry["kind"]}!')

        stream = dal.DROStreamConf(
            f"DROStream-{source_id}",
            source_id=entry["src_id"],
            stream_params=stream_pars,
            geo_id=geo_dal
        )
        db.update_dal(stream)
        if entry["kind"] == "eth":
            eth_streams.append(stream)
        else:
            flx_streams.append(stream)
        last_source_id = source_id
        stream_dals[source_id] = stream

    if eth_streams_found:
        nic_name = f"nic-{last_eth_pars['rx_host']}"
        print(
            f"Ending by adding nic {last_eth_pars['rx_mac']} with id {nic_name}"
        )
        nic_dal = dal.NICInterface(
            nic_name,
            rx_hostname=last_eth_pars["rx_host"],
            rx_mac=last_eth_pars["rx_mac"],
            rx_ip=last_eth_pars["rx_ip"],
            rx_iface=last_eth_pars["rx_iface"],
            rx_pcie_addr=last_eth_pars["rx_pcie_dev"],
            contains=eth_streams,
            configuration=nic_config_dal
        )
        nic_dals[nic_name] = nic_dal
        db.update_dal(nic_dal)
        rogroup_dal = dal.ReadoutGroup(f"group-{eth_source_id}", contains=[nic_dal])
        db.update_dal(rogroup_dal)
        groups.append(rogroup_dal)

        address_table_dal = dal.IpbusAddressTable("Hermes-addrtab")
        db.update_dal(address_table_dal)
        # Loop over the json again to generate the Hermes links and controllers
        last_pars = None
        link_number = 0
        links = []
        last_tx_mac = None
        for entry in jsonmap:
            if entry["kind"] == "eth":
                pars = entry["parameters"]
                if last_pars != None:
                    if pars["tx_host"] != last_pars['tx_host']:
                        # print(f"Adding HermesController {hermes_id} for {pars['tx_host']=} {last_pars['tx_host']=}")
                        hermes_controller_dal = dal.HermesController(
                            hermes_id,
                            uri=f"ipbusudp-2.0://{last_pars['tx_host']}:50001",
                            address_table=address_table_dal,
                            links=links
                        )
                        db.update_dal(hermes_controller_dal)
                        links = []
                        link_number = 0

                geo_id = entry["geo_id"]
                hermes_id = f"hermes_{geo_id['det_id']}_{geo_id['crate_id']}_{geo_id['slot_id']}"
                source_id = entry["src_id"] + source_id_offset
                nic_name = f"nic-{pars['rx_host']}"
                hermes_link_id = f"{hermes_id}-{link_number}"
                if pars["tx_mac"] != last_tx_mac:
                    link_dal = dal.HermesLinkConf(
                        hermes_link_id,
                        link_id=link_number,
                        source=stream_dals[source_id],
                        destination=nic_dals[nic_name]
                    )
                    db.update_dal(link_dal)
                    links.append(link_dal)
                    link_number = link_number + 1
                last_pars = pars
                last_tx_mac = pars["tx_mac"]
                last_tx_host = pars["tx_host"]
        if link_number > 0:
            # print(f"Adding HermesController {hermes_id}")
            hermes_controller_dal = dal.HermesController(
                hermes_id,
                uri=f"ipbusudp-2.0://{last_pars['tx_host']}:50001",
                address_table=address_table_dal,
                links=links
            )
            db.update_dal(hermes_controller_dal)


    if flx_streams_found and len(flx_streams) > 0:
        print(f"Adding final FelixInterface felix-{flx_source_id}")
        felix_dal = dal.FelixInterface(
            f"felix-{flx_source_id}",
            card=last_felix_pars["card"],
            slr=last_felix_pars["slr"],
            contains=flx_streams
        )
        db.update_dal(felix_dal)
        rogroup_dal = dal.ReadoutGroup(f"group-{flx_source_id}", contains=[felix_dal])
        db.update_dal(rogroup_dal)
        groups.append(rogroup_dal)

    if not nomap:
        map_dal = dal.ReadoutMap("readoutmap", groups=groups)
        db.update_dal(map_dal)


    db.commit()
