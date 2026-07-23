import conffwk
import json
from logging import getLogger
import sys
from rich import print
log = getLogger('daqconf.jsonify')


def hash_function(obj: object) -> int:
    # I guess we could get ObjectId from MongoDB
    return hash(f'{obj.id}@{obj.className()}')


def convert_to_dict(db: conffwk.Configuration, obj: object) -> dict[str, str | int]:
    dal_dict = {
        "__type": obj.className(),
        "_id": {
            "$oid": hash_function(obj), # Borrowing from MongoDB
        }
    }

    for attribute_name, attribute_value in db.attributes(obj.className(), all=True).items():
        dal_dict[attribute_name] = getattr(obj, attribute_name)

    for relation_name, relation_value in db.relations(obj.className(), all=True).items():
        relation_object = getattr(obj, relation_name, None)

        if relation_object is None:
            dal_dict[relation_name] = None

        elif not relation_value.get('multivalue', False):
            dal_dict[relation_name] = {
                # "$ref": "run-registry"
                '$id': hash_function(relation_object),
            }

        else:
            dal_dict[relation_name] = [
                {
                    "$id": hash_function(one_relation_object)
                    # "$ref": "run-registry"
                }
                for one_relation_object in relation_object
            ]

    return dict(sorted(dal_dict.items()))


def jsonify_xml_data(oksfile: str, output: str) -> None:

    sys.setrecursionlimit(10000)

    log.info(f"JSonifying database \'{oksfile}\' to \'{output}\'.")

    log.debug("Reading database")
    db = conffwk.Configuration("oksconflibs:" + oksfile)

    dals = db.get_all_dals()
    the_big_dict = {}

    for dal_str in dals:
        dal = dals[dal_str]
        key_name = f"{dal.id}@{dal.className()}"
        log.debug(f"Processing DAL {key_name}")
        if key_name in the_big_dict:
            log.error(f"Duplicate DAL id {key_name}")
            continue

        dal_dict = convert_to_dict(db, dal)
        the_big_dict[key_name] = dal_dict

    with open(output, 'w') as f:
        json.dump(dict(sorted(the_big_dict.items())), f, indent=4)

