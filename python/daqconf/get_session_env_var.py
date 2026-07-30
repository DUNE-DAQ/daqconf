import conffwk
import confmodel_dal
import sys

def get_session_env_var(
        oksfile: str, session_name: str, requested_env_var_name: str, quiet: bool = False
) -> str | None:
    """Script to get the value of an environment variable in the specified Session of the
    specified OKS database file"""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if session_name == "":
        if not quiet:
            print(f"Error: the session name needs to be specified", file=sys.stderr)
        return
    else:
        try:
            session = db.get_dal("Session", session_name)
        except:
            if not quiet:
                print(f"Error: could not find Session \"{session_name}\" in file \"{oksfile}\"", file=sys.stderr)
            return

    schemafiles = [
        "schema/confmodel/dunedaq.schema.xml"
    ]
    dal = conffwk.dal.module("dal", schemafiles)

    # Check if the requested env var is defined for the specified OKS Session
    existing_env_var = None
    for entry in session.environment:
        if isinstance(entry, dal.VariableSet):
            for subentry in entry.contains:
                if subentry.name == requested_env_var_name:
                    existing_env_var = subentry
                    break
        else:
            if entry.name == requested_env_var_name:
                existing_env_var = entry

        if existing_env_var is not None:
            break

    # Return the value, or complain and return None if the env var was not found
    if existing_env_var is None:
        if not quiet:
            print(f"Error: could not find env var \"{requested_env_var_name}\" in Session \"{session_name}\"", file=sys.stderr)
        return
    else:
        value = existing_env_var.value
        return value
