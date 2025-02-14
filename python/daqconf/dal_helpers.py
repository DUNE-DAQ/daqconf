"""
"""
##
# Dal helpers
#
def get_attribute_info(o):
    return o.__schema__['attribute']

def get_relation_info(o):
    return o.__schema__['relation']

def get_attribute_list(o):
    return list(get_attribute_info(o))

def get_relation_list(o):
    return list(get_relation_info(o))

def get_superclass_list(o):
    return o.__schema__['superclass']

def get_subclass_list(o):
    return o.__schema__['subclass']

def compare_dal_obj(a, b):
    """Compare two dal objects by content"""

    # TODO: add a check on a and b being dal objects
    # There is no base class for dal objects in python, but dal objects have _shcema__objects.
    

    if a.className() != b.className():
        return False

    attrs = get_attribute_list(a)
    rels = get_relation_list(a)

    a_attrs = {x:getattr(a, x) for x in attrs}
    b_attrs = {x:getattr(b, x) for x in attrs}

    a_rels = {x:getattr(a, x) for x in rels}
    b_rels = {x:getattr(b, x) for x in rels}


    return (a_attrs == b_attrs) and (a_rels == b_rels)


#---------------
def find_related(dal_obj, dal_group: set):


    rels = get_relation_list(dal_obj)

    rel_objs = set()
    for rel in rels:
        rel_val = getattr(dal_obj, rel)

        if rel_val is None:
            continue

        rel_objs.update(rel_val if isinstance(rel_val,list) else [rel_val])

    # Isolate relationship objects that are not in the dal_group yet
    new_rel_objs = rel_objs - dal_group

    # Safely add the new object to the group
    dal_group.update(rel_objs)
    for o in new_rel_objs:
        if o is None:
            continue

        find_related(o, dal_group)
        
from collections.abc import Iterable
def find_duplicates( collection: Iterable ):
    """
    Find duplicated dal objects in a collection by comparing objects attributes and relationships
    """
    
    n_items = len(collection)
    duplicates = set()
    for i in range(n_items):
        for j in range(i+1, n_items):
            if compare_dal_obj(collection[i], collection[j]):
                duplicates.add(collection[i])
                duplicates.add(collection[j])

    return duplicates

