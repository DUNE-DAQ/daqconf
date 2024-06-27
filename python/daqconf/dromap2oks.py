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
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
        "schema/appmodel/fdmodules.schema.xml",
    ]
    dal = conffwk.dal.module("generated", schemafiles[2])
    db = conffwk.Configuration("oksconflibs")
    db.create_db(oksfile, schemafiles)

    eth_streams = []
    hermes_streams = []
    flx_streams = []
    eth_senders = []
    flx_senders = []
    links = []
    last_eth_pars = None
    last_felix_pars = None
    last_hermes_id = None
    eth_streams_found = False
    flx_streams_found = False

    rx_queue = 0
    link_number = 0
    last_tx_mac = None
    last_tx_host = None
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

        stream_dal = dal.DetectorStream(f"stream-{source_id}",
                                        source_id = source_id,
                                        geo_id = geo_dal
                                        )
        db.update_dal(stream_dal)

        if entry["kind"] == "eth":
            eth_source_id = source_id
            if not eth_streams_found:
                eth_streams_found = True
                lcore_dal = dal.ProcessingResource(
                    f"lcores-{group_name}",
                    cpu_cores = lcores.split(',')
                )
                db.update_dal(lcore_dal)
                nic_config_dal = dal.DPDKPortConfiguration(
                    f"nicConfig-{group_name}",
                    used_lcores = [ lcore_dal ]
                )
                db.update_dal(nic_config_dal)
                address_table_dal = dal.IpbusAddressTable("Hermes-addrtab")
                db.update_dal(address_table_dal)


            pars = entry["parameters"]
            if last_eth_pars == None or pars["rx_mac"] != last_eth_pars["rx_mac"]:
                nic_name = f"nic-{pars['rx_host']}"
                print(f"New nic adding nic {pars['rx_mac']} with id {nic_name}")
                rxnic_dal = dal.NICInterface(
                    nic_name,
                    mac_address = pars["rx_mac"],
                    ip_address = pars["rx_ip"]
                )
                db.update_dal(rxnic_dal)

                dpdkrec_dal = dal.DPDKReceiver(
                    f"{pars['rx_host']}-receiver",
                    uses = rxnic_dal,
                    configuration = nic_config_dal
                )
                db.update_dal(dpdkrec_dal)



            if last_tx_mac != None and pars["tx_mac"] != last_tx_mac:
                link_dal = dal.HermesDataSender(
                    hermes_link_id,
                    link_id = link_number,
                    contains = hermes_streams,
                    uses = txnic_dal
                )
                db.update_dal(link_dal)
                links.append(link_dal)
                link_number = link_number + 1
                eth_senders.append(link_dal)
                hermes_streams = []

            if last_tx_mac == None or pars["tx_mac"] != last_tx_mac:
                if last_tx_host != pars['tx_host']:
                    nic_num = -1
                nic_num += 1
                nic_name = f"nic-{pars['tx_host']}-{nic_num}"
                print(f"Adding NIC {nic_name}")
                txnic_dal = dal.NICInterface(
                    nic_name,
                    mac_address = pars["tx_mac"],
                    ip_address = pars["tx_ip"]
                )
                db.update_dal(txnic_dal)

            if last_eth_pars != None:
                if pars["tx_host"] != last_eth_pars['tx_host']:
                    # print(f"Adding HermesModule {hermes_id} for {pars['tx_host']=} {last_pars['tx_host']=}")
                    hermes_controller_dal = dal.HermesModule(
                        hermes_id,
                        uri = f"ipbusudp-2.0://{last_eth_pars['tx_host']}:50001",
                        address_table = address_table_dal,
                        links = links,
                        destination = rxnic_dal
                    )
                    db.update_dal(hermes_controller_dal)
                    links = []
                    link_number = 0

                #print(f"streams in nic {pars['rx_mac']} = {len(streams)}")
                if pars["rx_mac"] != last_eth_pars["rx_mac"]:
                    rset_dal = dal.ResourceSetAND(
                        f"{last_eth_pars['rx_host']}-senders",
                        contains = eth_senders
                    )
                    db.update_dal(rset_dal)
                    daqcon_dal = dal.DetectorToDaqConnection(
                        f"{last_eth_pars['rx_host']}-connections",
                        contains = [rset_dal, dpdkrec_dal]
                    )
                    db.update_dal(daqcon_dal)

                    rset_dal = dal.ResourceSetAND(
                        f"{last_eth_pars['rx_host']}-streams",
                        contains = eth_streams
                    )
                    db.update_dal(rset_dal)

                    eth_streams = []
                    hermes_streams = []
                    eth_senders = []
                    rx_queue = 0
            # Update Hermes ids now _after_ making any DataSenders or
            # Controllers since we don't make them for the current
            # params but the ones from the loop before
            hermes_id = f"hermes_{geo_id['det_id']}_{geo_id['crate_id']}_{geo_id['slot_id']}"
            hermes_link_id = f"{hermes_id}-{link_number}"
            if pars != last_eth_pars:
                rx_queue = rx_queue + 1
                last_eth_pars = pars
                last_eth_source_id = source_id
                last_tx_mac = pars["tx_mac"]
                last_tx_host = pars["tx_host"]


        elif entry["kind"] == "flx":
            print (f"Processing config for FELIX {source_id=}")
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
                        slr=last_felix_pars["slr"]
                    )
                    db.update_dal(felix_dal)
                    rset_dal = dal.ResourceSetAND(
                        f"felix-{last_source_id}-streams",
                        contains = flx_streams
                    )
                    db.update_dal(rset_dal)
                    daqcon_dal = dal.DetectorToDaqConnection(
                        f"felix-{last_source_id}-connections",
                        contains = [rset_dal, felix_dal]
                    )
                    db.update_dal(daqcon_dal)
                    flx_streams = []
            # Not sure how FelixDataSender fits in. What uses it?
            flx_sender_dal = dal.FelixDataSender(
                f"flxsender-{source_id}",
                protocol=pars["protocol"],
                link=pars["link"],
                contains = [stream_dal]
            )
            db.update_dal(flx_sender_dal)
            flx_senders.append(flx_sender_dal)
            last_felix_pars = pars
            last_felix_source_id = source_id
        else:
            raise RuntimeError(f'Unknown kind of readout {entry["kind"]}!')

        if entry["kind"] == "eth":
            eth_streams.append(stream_dal)
            hermes_streams.append(stream_dal)
        else:
            flx_streams.append(stream_dal)

        last_source_id = source_id

    if eth_streams_found:
        if link_number > 0:
            print(f"Adding final HermesDataSender {hermes_link_id}")
            if len(eth_streams) > 0:
                link_dal = dal.HermesDataSender(
                    hermes_link_id,
                    link_id = link_number,
                    contains = hermes_streams,
                    uses = txnic_dal
                )
                db.update_dal(link_dal)
                links.append(link_dal)
            print(f"Adding final HermesModule {hermes_id}")
            hermes_controller_dal = dal.HermesModule(
                hermes_id,
                uri = f"ipbusudp-2.0://{last_eth_pars['tx_host']}:50001",
                address_table = address_table_dal,
                links = links,
                destination = rxnic_dal
            )
            db.update_dal(hermes_controller_dal)


        rset_dal = dal.ResourceSetAND(
            f"{last_eth_pars['rx_host']}-senders",
            contains = eth_senders
        )
        db.update_dal(rset_dal)
        rset_dal = dal.ResourceSetAND(
            f"{last_eth_pars['rx_host']}-streams",
            contains = eth_streams
        )
        db.update_dal(rset_dal)
        daqcon_dal = dal.DetectorToDaqConnection(
            f"{last_eth_pars['rx_host']}-connections",
            contains = [rset_dal, dpdkrec_dal]
        )
        db.update_dal(daqcon_dal)


    if flx_streams_found and len(flx_senders) > 0:
        print(f"Adding final FelixInterface felix-{flx_source_id}")
        felix_dal = dal.FelixInterface(
            f"felix-{flx_source_id}",
            card=last_felix_pars["card"],
            slr=last_felix_pars["slr"]
        )
        db.update_dal(felix_dal)
        rset_dal = dal.ResourceSetAND(
            f"felix-{flx_source_id}-streams",
            contains = flx_streams
        )
        db.update_dal(rset_dal)
        daqcon_dal = dal.DetectorToDaqConnection(
            f"felix-{flx_source_id}-connections",
            contains = [rset_dal, felix_dal]
        )
        db.update_dal(daqcon_dal)

    db.commit()
