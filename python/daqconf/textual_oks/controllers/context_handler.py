#!/usr/bin/env python3
"""
TODO : Add type checking
"""

import conffwk
import confmodel

from textual.widgets import Static

class ContextHandler(Static):

   _input_config = reactive(None)
   _dal_input_config = reactive(None)

   _current_selected_dal = reactive(None)

   @property
   def input_config(self):
       return self._input_config

   @input_config.setter
   def input_config(self, new_config):
       self._input_config = new_config


    @property
    def dal_input_config(self):
        return self._dal_input_config

    @dal_input_config.setter
    def dal_input_config(self, new_dal_config):
        self._dal_input_config = new_dal_config


    @property
    def current_selected_dal(self):
        return self._current_selected_dal


    @current_selected_dal.setter
    def current_selected_dal(self, new_current_dal):
        self._current_selected_dal = new_current_dal

    def open_configs_from_file(self, file_name: str, class_name: str, class_uid: str)->bool:
        # Check if file exists
        if not os.path.isfile(file_name):
            #file_pretty.update(f"Couldn't find {file_name}")
            return False

        # Try opening config
        try:
            self._input_config = conffwk.Configuration(f"oksconflibs:{file_name}")
        except:
            #file_pretty.update(f"{file_name} not a valid OKS config")
            return False

        file_pretty.update(f"Found {file_name}")

        # Try grabbing dal
        try:
            self._dal_input_config =  self._input_config.get_dal(class_name, class_uid)
        except:
            #class_pretty.update(f"Error couldn't find {uid_name.value}@{class_name.value} in {file_search.value}")
            return False

        #class_pretty.update(f"Found {uid_name.value}@{class_name.value}")
        return True

    def get_current_config(self, new_dal_config):
        # Set config
        self.dal_input_config = new_dal_config
