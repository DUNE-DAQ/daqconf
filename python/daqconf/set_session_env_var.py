import conffwk
import confmodel

def set_session_env_var(oksfile, session_name, requested_env_var_name, requested_env_var_value, overwrite=True):
    """Script to set the value of an environment variable in the specified Session of the
    specified OKS database file"""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if session_name == "":
        print(f"Error: the session name needs to be specified")
        return
    else:
        try:
            session = db.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {oksfile}")
            return

    schemafiles = [
        "schema/confmodel/dunedaq.schema.xml"
    ]
    dal = conffwk.dal.module("dal", schemafiles)

    # First, check if the requested env var is already defined for the specified OKS Session
    existing_env_var = None
    for entry in session.environment:
        if isinstance(entry, dal.VariableSet):
            for subentry in entry.contains:
                if subentry.name == requested_env_var_name:
                    existing_env_var = subentry
                    existing_env_var.value = requested_env_var_value
                    break
        else:
            if entry.name == requested_env_var_name:
                existing_env_var = entry
                existing_env_var.value = requested_env_var_value

        if existing_env_var is not None:
            break

    # if we found an existing env var, and we have been told not to over-write it, exit now
    if existing_env_var is not None and not overwrite:
        return

    # if we found an existing env var, update the DB with the new value
    if existing_env_var is not None:
        db.update_dal(existing_env_var)

    # otherwise, create a new env var and assign it to the OKS Session
    else:
        # 03-Jul-2025, KAB: switched from using a "temporary" string in the dal_name
        # to using the session name. This means that each Session will get its own
        # instance of the DAL Variable, which seems safer than having the possibility
        # of multiple Sessions sharing the same Variable.
        new_env_var_dal_name = session_name + "-env-var-" + requested_env_var_name
        new_env_var_dal_name = new_env_var_dal_name.lower()
        new_env_var_dal_name = new_env_var_dal_name.replace("_", "-")

        new_env_var = dal.Variable(new_env_var_dal_name, name=requested_env_var_name, value=requested_env_var_value)
        db.update_dal(new_env_var)

        session.environment.append(new_env_var)
        db.update_dal(session)

    # commit all changes
    db.commit()
