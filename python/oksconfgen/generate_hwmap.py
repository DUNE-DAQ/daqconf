import conffwk
import os
import json
import sys

def generate_hwmap(oksfile, n_streams, n_apps = 1, det_id = 3, app_host = "localhost",
                             eth_protocol = "udp", flx_mode = "fix_rate"):

    schemafiles = [
        "schema/coredal/dunedaq.schema.xml",
        "schema/appdal/application.schema.xml",
        "schema/appdal/fdmodules.schema.xml",
    ]
    dal = conffwk.dal.module("generated", schemafiles[2])
    db = conffwk.Configuration("oksconflibs")
    db.create_db(oksfile, schemafiles)

    group_name = os.path.basename(oksfile).removesuffix(".data.xml")
    groups = []
    streams = []
    source_id = 0

    stream_pars = dal.StreamParameters(
        f"dummyStream-1",
        mode=flx_mode,
    )

    db.update_dal(stream_pars)

    for app in range(n_apps):

        for stream_no in range(n_streams):

            geo_dal = dal.GeoId(
                f"geioId-{source_id}",
                detector_id=det_id,
                crate_id=app+1,
                slot_id=0,
                stream_id=stream_no,
            )
            db.update_dal(geo_dal)
            stream = dal.DROStreamConf(
                f"DROStream-{source_id}",
                source_id=source_id,
                stream_params=stream_pars,
                geo_id=geo_dal,
            )
            db.update_dal(stream)
            streams.append(stream)
            source_id = source_id + 1

        print(f"New nic adding nic with id nic-{app}")
        nic_dal = dal.ReadoutInterface(
            f"ROInterface-{app}",
            contains=streams,
        )
        db.update_dal(nic_dal)
        rogroup_dal = dal.ReadoutGroup(f"group-{app}", contains=[nic_dal])
        db.update_dal(rogroup_dal)
        groups.append(rogroup_dal)
        streams = []

    map_dal = dal.ReadoutMap("readoutmap", groups=groups)
    db.update_dal(map_dal)
    db.commit()

