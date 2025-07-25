import conffwk
import confmodel_dal

import re
import socket

def set_connectivity_service_port(oksfile, session_name, connsvc_port=0):
    """Script to set the value of the Connectivity Service port in the specified Session of the specified
    OKS database file. If the new port is not specified, it is set to a random available port number."""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if session_name == "":
        print(f"Error: the session name needs to be specified")
        return 0
    else:
        try:
            session = db.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {oksfile}")
            return 0

    schemafiles = [
        "schema/confmodel/dunedaq.schema.xml"
    ]
    dal = conffwk.dal.module("dal", schemafiles)

    if connsvc_port == 0:
        def find_free_port():
            with socket.socket() as s:
                s.bind(("", 0))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                port = s.getsockname()[1]
                s.close()
                return port

        new_port = find_free_port()
    else:
        new_port = connsvc_port

    if session.connectivity_service is not None:
        session.connectivity_service.service.port = new_port
        db.update_dal(session.connectivity_service.service)

    for app in session.infrastructure_applications:
        if app.className() == "ConnectionService":
            index = 0
            for clparam in app.commandline_parameters:
                if "gunicorn" in clparam:
                    pattern = re.compile(r'(.*0\.0\.0\.0)\:\d+(.*)')
                    app.commandline_parameters[index] = pattern.sub(f'\\1:{new_port}\\2', clparam)
                    #print(f"{app}")
                    db.update_dal(app)
                    break
                index += 1

    db.commit()
    return new_port
