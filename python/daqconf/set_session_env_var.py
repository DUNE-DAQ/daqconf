import conffwk
import confmodel

import os
import glob


def set_session_env_var(oksfile, env_var_name, env_var_value, session_name):
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

    dal_name = "session-env-" + env_var_name
    dal_name = dal_name.lower()
    dal_name = dal_name.replace("_", "-")

    schemafiles = [
        "schema/confmodel/dunedaq.schema.xml"
    ]
    dal = conffwk.dal.module("dal", schemafiles)
    new_or_updated_env = dal.Variable(dal_name, name=env_var_name, value=env_var_value)
    db.update_dal(new_or_updated_env)

    if not new_or_updated_env in session.environment:
        session.environment.append(new_or_updated_env)
        db.update_dal(session)

    db.commit()
