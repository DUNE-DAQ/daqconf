import conffwk
import confmodel_dal
from daqconf.utils import find_free_port

def set_connectivity_service_port(oksfile, session_name, connsvc_port=0):
    """Script to set the value of the Connectivity Service port in the specified Session of the specified
    OKS database file. If the new port is not specified, it is set to a random available k8s NodePort."""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if not session_name:
        print("Error: the session name needs to be specified")
        return 0
    else:
        try:
            session = db.get_dal("Session", session_name)
        except Exception:
            print(f"Error: could not find Session {session_name} in file {oksfile}")
            return 0

    k8s_min_port, k8s_max_port = 30000, 32767
    if connsvc_port == 0:
        new_port = find_free_port(k8s_min_port, k8s_max_port)
        print(f"Found free Kubernetes NodePort: {new_port}")
    else:
        new_port = connsvc_port
        if not (k8s_min_port <= new_port <= k8s_max_port):
            print(f"Warning: Port {new_port} is outside the standard k8s NodePort range ({k8s_min_port}-{k8s_max_port}).")

    # Update the Service
    if session.connectivity_service is not None:
        session.connectivity_service.service.port = new_port
        db.update_dal(session.connectivity_service.service)
        print(f"Updated Connectivity Service '{session.connectivity_service.service.id}' to use port {new_port}")
    else:
        print(f"Error: Session '{session_name}' has no connectivity_service defined. Skipping Service object update.")
        return 0

    # Update the env var
    if hasattr(session, 'environment') and session.environment is not None:
        found_var = False
        for item in session.environment:
            if item.className() == 'VariableSet':
                for var in item.contains:
                    if var.name == "CONNECTION_PORT":
                        var.value = str(new_port)
                        db.update_dal(var)
                        print(f"Updated runtime environment variable '{var.id}' to '{new_port}'")
                        found_var = True
                        break
            elif item.className() == 'Variable':
                if item.name == "CONNECTION_PORT":
                    item.value = str(new_port)
                    db.update_dal(item)
                    print(f"Updated runtime environment variable '{item.id}' to '{new_port}'")
                    found_var = True

            if found_var:
                break

        if not found_var:
            print("Error: Could not find a 'CONNECTION_PORT' variable in the session's environment.")
            return 0
    else:
        print("Error: Session has no 'environment' configured. Cannot update CONNECTION_PORT variable.")
        return 0

    db.commit()
    print(f"Successfully configured connectivity service port for session '{session_name}'.")
    return new_port
