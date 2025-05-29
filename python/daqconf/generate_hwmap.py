#!/usr/bin/env python3

import conffwk
import os
import json
import sys

def generate_hwmap(oksfile, n_streams, n_apps = 1, det_id = 3, app_host = "localhost",
                             eth_protocol = "udp", flx_mode = "fix_rate"):

    schemafiles = [
        "schema/confmodel/dunedaq.schema.xml",
        "schema/appmodel/application.schema.xml",
        "schema/appmodel/fdmodules.schema.xml",
        "schema/appmodel/wiec.schema.xml",
    ]
    dal = conffwk.dal.module("generated", schemafiles[-1])
    db = conffwk.Configuration("oksconflibs")
    db.create_db(oksfile, schemafiles)

    group_name = os.path.basename(oksfile).removesuffix(".data.xml")
    groups = []
    streams = []
    senders = []
    source_id = 0

    for app in range(n_apps):
        print (f"Generating {app=}")
        print(f"New nic adding nic with id nic-{app}")
        nic_dal = dal.NetworkInterface(f"nic-{app}")
        db.update_dal(nic_dal)

        for stream_no in range(n_streams):
            print (f"Generating {stream_no=}")

            geo_dal = dal.GeoId(
                f"geioId-{source_id}",
                detector_id=det_id,
                crate_id=app+1,
                slot_id=0,
                stream_id=stream_no,
            )
            db.update_dal(geo_dal)
            stream = dal.DetectorStream(
                f"stream-{source_id}",
                source_id=source_id,
                geo_id=geo_dal,
            )
            db.update_dal(stream)
            streams.append(stream)
            db.commit()

            sender_dal = dal.FakeDataSender(
                f"sender-{source_id}",
                streams=[stream],
                uses=nic_dal
            )
            db.update_dal(sender_dal)
            senders.append(sender_dal)
            db.commit()

            source_id = source_id + 1

        rec_dal = dal.FakeDataReceiver(
            f"dataRec-{app}",
            uses=nic_dal
        )
        db.update_dal(rec_dal)
        detconn_dal = dal.NetworkDetectorToDaqConnection(
            f"det-conn-{app}",
            net_receiver=rec_dal,
            net_senders=senders
        )
        db.update_dal(detconn_dal)
        groups.append(detconn_dal)
        senders = []

    db.commit()

if __name__ == "__main__":
    generate_hwmap("xxx.data.xml", 4, n_apps=2)
