import conffwk
import confmodel_dal


def compare_objects(obj1: object, obj2: object) -> bool:
  """ Compare 2 dal objects for equality attribute by attribute """
  same = True
  if type(obj1) != type(obj2):
    print (f"ERROR objects are not the same type {type(obj1)} != {type(obj2)}")
    return False

  ign=['__id', '__fullname__', '__hashvalue__', '__touched__']

  d1 = obj1.__dict__
  d2 = obj2.__dict__
  for key in d1:
    if key in ign:
      continue
    if key in d2:
      #print (f"    Comparing {obj1.id}[{key}] ({d1[key]}) with {obj2.id}[{key}] ({d2[key]})")
      ##print (f"    Comparing {d1[key]=} with {d2[key]=}")
      if d1[key] != d2[key]:
        #print (f"    difference {obj1.id}[{d1[key]}] != {obj2.id}[{d2[key]}]")
        same=False
        break
    else:
      print (f"Error attribute names {key} not common")
      same=False
      break
  return same



def check_unique_relationship(objects: list[object], relationship: str) -> bool:
  """
  Check to see if the given relationship (by class name) is unique
  among a list of objects. First by comparing the UIDs, then by
  comparing the values within.
  """

  seen = []
  seen_id = {}
  unique = True
  for obj in objects:
    print(f"Checking {obj.id}")
    rel = obj.get(relationship)
    if len(rel) < 1:
      print(f"No object found for relationship {relationship} in {obj.id}")
      continue
    #print (f"Found {len(rel)} objects of type {relationship} in {obj.id}")
    for val in rel:
      if val.id in seen_id:
        print (
          f"ERROR {obj.id}:  {val.className()} {val.id} already seen in {seen_id[val.id]}")
        unique = False
      else:
        for other in seen:
          #print (f"  Checking {val.id}=={other.id}?")
          if compare_objects(val, other):
            print (f"object {obj.id} {val.id} is same as {other.id}")
            unique = False
      if not unique:
        break
      seen.append(val)
      seen_id[val.id] = obj.id
  return unique


def validate_readout(db: conffwk.Configuration, session: object) -> int:
  errcount = 0
  # Find all enabled readout apps and check that
  # DetectorToDaqConnection's are unique
  ru_apps = []
  for app in confmodel_dal.session_get_all_applications(db._obj, session.id):
    if confmodel_dal.component_disabled(db._obj, session.id, app.id):
      continue

    app_dal = db.get_dal(app.class_name, app.id)
    if "ReadoutApplication" in app_dal.oksTypes():
      ru_apps.append(app_dal)

  if len(ru_apps) == 0:
    print(f"No enabled readout applicatios in session")
    errcount += 1
  d2d_seen = {}
  d2d_dals = []
  snd_dals = []
  senders_seen = {}
  for ru in ru_apps:
    connections = 0
    for d2d in ru.detector_connections:
      if d2d.id in d2d_seen:
        print(f"Error {ru.id} contains {d2d.id}"+
              f" which is already read out by {d2d_seen[d2d.id]}")
        errcount += 1
        continue

      senders = 0
      for sndr in confmodel_dal.d2d_senders(db._obj, d2d.id):
        if sndr in senders_seen:
          print(f"Error sender {sndr.id} already seen in {senders_seen[sndr.id]}")
          errcount += 1
          continue
        senders_seen[sndr] = d2d.id
        snd_dals.append(db.get_dal("DetDataSender", sndr))
        senders += 1
      if senders == 0:
        print(f"Error {d2d.id} does not have any senders")
        errcount += 1
        continue
      if confmodel_dal.d2d_receiver(db._obj, d2d.id) == "":
        print(f"Error {d2d.id} does not have a receiver")
        errcount += 1
        continue
      d2d_seen[d2d.id] = ru.id
      d2d_dals.append(d2d)
      connections += 1
    if connections == 0:
      print(f"Error {ru.id} contains 0 detector connections")
      errcount += 1

  print (f"\nChecking data senders for duplicate streams");
  if not check_unique_relationship(snd_dals, "DetectorStream"):
    errcount += 1

  print (f"\nChecking detector connections for duplicate geio ids")
  if not check_unique_relationship(d2d_dals, "GeoId"):
    errcount += 1

  print (f"Session {session.id} readout validated with {errcount} errors:"+
         f" contains {len(d2d_seen)} Detector connections"+
         f" in {len(ru_apps)} readout applications")

  return errcount

def validate_session(oksfile: str, session_name: str) -> None:
  db = conffwk.Configuration("oksconflibs:" + oksfile)
  if session_name == "":
    session_dals = db.get_dals(class_name="Session")
    if len(session_dals) == 0:
      print(f"Error could not find any Session in file {oksfile}")
      return
    if len(session_dals) > 1:
      print(f"Warning: more than one Session found in database."
            " Using the first one found")
    session = session_dals[0]
  else:
    try:
      session = db.get_dal("Session", session_name)
    except:
      print(f"Error could not find Session {session_name} in file {oksfile}")
      return

  print(f"Validating session {session.id}:")
  errcount = validate_readout(db, session)
  print (f"\nSession {session.id} validated with {errcount} errors")
