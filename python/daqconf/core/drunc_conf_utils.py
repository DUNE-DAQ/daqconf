


def get_controller_conf(apps, kafka_address):
    return {
        "children": [
            {
                'name': a['name'],
                'uri': f'{a["host"]}:{a["port"]}', # "uri": "np04-srv-012:3333"
                'type': 'rest-api'
            }
            for a in apps
        ],

        "broadcaster": {
            "type": "kafka",
            "kafka_address": kafka_address,
            "publish_timeout": 2
        },

        "statefulnode": {
            "included": True,
            "fsm":{
                "states": [
                    "initial", "configured", "ready", "running",
                    "paused", "dataflow_drained", "trigger_sources_stopped", "error"
                ],
                "initial_state": "initial",
                "transitions": [
                    { "trigger": "conf",                 "source": "initial",                 "dest": "configured"             },
                    { "trigger": "start",                "source": "configured",              "dest": "ready"                  },
                    { "trigger": "enable_triggers",      "source": "ready",                   "dest": "running"                },
                    { "trigger": "disable_triggers",     "source": "running",                 "dest": "ready"                  },
                    { "trigger": "drain_dataflow",       "source": "ready",                   "dest": "dataflow_drained"       },
                    { "trigger": "stop_trigger_sources", "source": "dataflow_drained",        "dest": "trigger_sources_stopped"},
                    { "trigger": "stop",                 "source": "trigger_sources_stopped", "dest": "configured"             },
                    { "trigger": "scrap",                "source": "configured",              "dest": "initial"                }
                ],
                "command_sequences": {
                    "start_run": [
                        {"cmd": "conf",            "optional": True },
                        {"cmd": "start",           "optional": False},
                        {"cmd": "enable_triggers", "optional": False}
                    ],
                    "stop_run" : [
                        {"cmd": "disable_triggers",     "optional": True },
                        {"cmd": "drain_dataflow",       "optional": False},
                        {"cmd": "stop_trigger_sources", "optional": False},
                        {"cmd": "stop",                 "optional": False}
                    ],
                    "shutdown" : [
                        {"cmd": "disable_triggers",     "optional": True },
                        {"cmd": "drain_dataflow",       "optional": True },
                        {"cmd": "stop_trigger_sources", "optional": True },
                        {"cmd": "stop",                 "optional": True },
                        {"cmd": "scrap",                "optional": True }
                    ]
                },
                "interfaces": {
                    "user-provided-run-number": {},
                },
                "pre_transitions": {
                    "start":  {"order": ["user-provided-run-number"], "mandatory": ["user-provided-run-number"]}
                },
                "post_transitions": {}
            }
        }
    }