import conffwk
import confmodel_dal
from daqconf.utils import find_free_port
import sys

def set_rc_controller_port(oksfile, session_name, rc_port=0):
    """
    Script to set the value of the RC Controller Service port used by the specified Session
    in the specified OKS database file. If the new port is not specified,
    it is set to a random available k8s NodePort.
    """
    try:
        db = conffwk.Configuration("oksconflibs:" + oksfile)
    except Exception as e:
        print(f"Error: Could not open OKS file {oksfile}. Make sure OKS_CONFLIBS_PATH is set.")
        print(f"Details: {e}")
        return 0

    if not session_name:
        print("Error: The session name needs to be specified")
        return 0
    else:
        try:
            session = db.get_dal("Session", session_name)
        except Exception:
            print(f"Error: Could not find Session '{session_name}' in file '{oksfile}'")
            return 0

    # Find a new port if one isn't specified
    k8s_min_port, k8s_max_port = 30000, 32767
    if rc_port == 0:
        new_port = find_free_port(k8s_min_port, k8s_max_port)
        print(f"Found free Kubernetes NodePort: {new_port}")
    else:
        new_port = rc_port
        if not (k8s_min_port <= new_port <= k8s_max_port):
            print(f"Warning: Port {new_port} is outside the standard k8s NodePort range ({k8s_min_port}-{k8s_max_port}).")

    # Traverse from Session -> Segment -> Controller -> Service
    service_to_update = None
    try:
        if not hasattr(session, 'segment') or session.segment is None:
            print(f"Error: Session '{session_name}' has no 'segment' defined.")
            return 0

        segment = session.segment
        if not hasattr(segment, 'controller') or segment.controller is None:
            print(f"Error: Segment '{segment.id}' has no 'controller' defined.")
            return 0

        controller = segment.controller
        if not hasattr(controller, 'exposes_service') or not controller.exposes_service:
            # Check if the attribute exists AND if the list is not empty
            print(f"Error: Controller '{controller.id}' has no 'exposes_service' defined or the list is empty.")
            return 0

        service_list = controller.exposes_service
        
        if len(service_list) > 1:
            print(f"Warning: Controller '{controller.id}' exposes multiple services. Only updating the first one ('{service_list[0].id}').")
        
        service_to_update = service_list[0]
        
        if service_to_update is None:
            print(f"Error: Controller '{controller.id}' has a null service in its 'exposes_service' list.")
            return 0

    except Exception as e:
        print(f"Error: Failed to navigate object graph from Session '{session_name}'.")
        print(f"Details: {e}")
        return 0

    # Update the Service
    if service_to_update:
        service_to_update.port = new_port
        db.update_dal(service_to_update)
        print(f"Updated RC Controller Service '{service_to_update.id}' to use port {new_port}")
        
        db.commit()
        print(f"Successfully configured RC controller port for session '{session_name}'.")
        return new_port
    else:
        # This case is mostly covered by the checks above, but serves as a fallback.
        print(f"Error: Could not find the RC Controller Service for session '{session_name}'.")
        return 0

