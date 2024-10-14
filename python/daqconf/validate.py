import conffwk
import confmodel


def compare_objects(obj1, obj2):
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



def check_unique_relationship(objects, relationship):
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


def validate_readout(db, system):
  errcount = 0
  # Find all enabled readout apps and check that
  # DetectorToDaqConnection's are unique
  ru_apps = []
  for app in confmodel.system_get_all_applications(db._obj, system.id):
    if confmodel.component_disabled(db._obj, system.id, app.id):
      continue
    if app.class_name == "ReadoutApplication":
      ru_apps.append(db.get_dal(app.class_name, app.id))
  if len(ru_apps) == 0:
    print(f"No enabled readout applicatios in system")
    errcount += 1
  d2d_seen = {}
  d2d_dals = []
  snd_dals = []
  senders_seen = {}
  for ru in ru_apps:
    connections = 0
    for d2d in ru.contains:
      if d2d.className() != "DetectorToDaqConnection":
        print(f"Error {ru.id} contains a {d2d.className()} where it should have a DetectorToDaqConnection")
        errcount += 1
        continue
      if d2d.id in d2d_seen:
        print(f"Error {ru.id} contains {d2d.id}"+
              f" which is already read out by {d2d_seen[d2d.id]}")
        errcount += 1
        continue

      senders = 0
      receiver = 0
      for d2d_res in d2d.contains:
        if "DetDataReceiver" in d2d_res.oksTypes():
          receiver += 1
        elif "DetDataSender" in d2d_res.oksTypes():
          if d2d_res.id in senders_seen:
            print(f"Error sender {d2d_res.id} already seen in {senders_seen[d2d_res.id]}")
            errcount += 1
            continue
          senders_seen[d2d_res.id] = d2d.id
          snd_dals.append(d2d_res)
          senders += 1
        elif "ResourceSet" in d2d_res.oksTypes():
          for snd_res in d2d_res.contains:
            if "DetDataSender" in snd_res.oksTypes():
              if snd_res.id in senders_seen:
                print(f"Error sender {snd_res.id} already seen in {senders_seen[d2d_res.id]}")
                errcount += 1
                continue
              senders_seen[snd_res.id] = d2d.id
              snd_dals.append(snd_res)
              senders += 1
      if senders == 0:
        print(f"Error {d2d.id} does not have any senders")
        errcount += 1
        continue
      if receiver == 0:
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

  print (f"System {system.id} readout validated with {errcount} errors:"+
         f" contains {len(d2d_seen)} Detector connections"+
         f" in {len(ru_apps)} readout applications")

  return errcount

def validate_system(oksfile, system_name):
  db = conffwk.Configuration("oksconflibs:" + oksfile)
  if system_name == "":
    system_dals = db.get_dals(class_name="System")
    if len(system_dals) == 0:
      print(f"Error could not find any System in file {oksfile}")
      return
    if len(system_dals) > 1:
      print(f"Warning: more than one System found in database."
            " Using the first one found")
    system = system_dals[0]
  else:
    try:
      system = db.get_dal("System", system_name)
    except:
      print(f"Error could not find System {system_name} in file {oksfile}")
      return

  print(f"Validating system {system.id}:")
  errcount = validate_readout(db, system)
  print (f"\nSystem {system.id} validated with {errcount} errors")
