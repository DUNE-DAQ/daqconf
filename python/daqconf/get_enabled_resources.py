from conffwk import Configuration

def get_enabled_resources(oksfile: str, session_name: str, resource_class="Resource"):
    """Function to list enabled resources in the specified OKS database file"""
    
    db = Configuration("oksconflibs:" + oksfile)  
    
    session = db.get_session(session_name)
    if not session:
        raise ValueError(f"Session '{session_name}' not found in database '{oksfile}'")

    enabled_resources = []
    enabled_resource_dals = []
    
    disabled_objects = session.disabled
    
    for resource in session.get_dals(resource_class):
        if not resource in disabled_objects:
            enabled_resources.append([getattr(resource, "id"), getattr(resource, "className")()])
            enabled_resource_dals.append(resource)
    
    return enabled_resources, enabled_resource_dals