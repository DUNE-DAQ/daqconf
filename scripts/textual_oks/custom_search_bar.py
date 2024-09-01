#!/usr/bin/env python3

'''
Object controller
'''

import conffwk
import confmodel

import os.path

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Pretty, Label, Button
from textual.reactive import reactive

class SearchBar(Static):
    """
    Controller object
    """
    _input_config = reactive(None)#reactive(conffwk.Configuration(f"oksconflibs:{input_file}"))      #conffwk.Configuration(f"oksconflibs:{input_file}")
    _dal_input_config = reactive(None) #input_config.get_dal(root_class_type, class_uid) #input_config.get_dal(root_class_type, class_uid)

    def compose(self)->ComposeResult:

        # File Name bar
        yield Label("File Name")
        yield Input(id="file_search")
        yield Pretty("[]", id="file_pretty")

        yield Label("Class Name")
        yield Input(id="class_search")

        yield Label("Class UID")
        yield Input(id="uid_search")
        yield Pretty("[]", id="class_pretty")

        # Search Button
        yield Button("Search", id="search_button")

    def open_configs(self)->bool:

        # Only care about this button
        file_search = self.query_one("#file_search")

        file_pretty = self.query_one("#file_pretty")

        # Check if file exists
        if not os.path.isfile(file_search.value):
            file_pretty.update(f"Couldn't find {file_search.value}")
            return False

        # Try opening config
        try:
            self._input_config = conffwk.Configuration(f"oksconflibs:{file_search.value}")
        except:
            file_pretty.update(f"{file_search.value} not a valid OKS config")
            return False

        file_pretty.update(f"Found {file_search.value}")

        class_name = self.query_one("#class_search")
        uid_name   = self.query_one("#uid_search")
        class_pretty = self.query_one("#class_pretty")

        # Try grabbing dal
        try:
            self._dal_input_config =  self._input_config.get_dal(class_name.value, uid_name.value)
        except:
            class_pretty.update(f"Error couldn't find {uid_name.value}@{class_name.value} in {file_search.value}")
            return False

        class_pretty.update(f"Found {uid_name.value}@{class_name.value}")
        return True


    def get_configs(self):
        return self._input_config, self._dal_input_config
