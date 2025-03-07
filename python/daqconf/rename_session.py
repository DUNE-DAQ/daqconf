import conffwk
import copy

def rename_session(oksfile,output_name,session_name=None):
    """Script to rename the session (first session if multiple and not specified)"""
    
    db = conffwk.Configuration('oksconflibs:'+oksfile)

    if session_name is not None:
        try:
            session = db.get_dal("Session",session_name)
        except:
            print(f"Error could not find Session {session_name} in file {oksfile}")
            return
    else:
        sessions = db.get_dals("Session")
        if len(sessions)==0:
            print(f"Error in {oksfile}: no sessions found.")
            return
        if len(sessions)>1:
            print(f"{oksfile} found {len(sessions)}. Will change name of first ({sessions[0].id})")
        session = sessions[0]
        
    new_session = copy.copy(session)
    setattr(new_session,"id",output_name)

    db.add_dal(new_session)
    db.destroy_dal(session)

    db.commit()
