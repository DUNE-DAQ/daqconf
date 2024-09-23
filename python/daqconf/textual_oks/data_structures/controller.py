from textual.widgets import Static

from data_structures.configuration import ConfigurationHandler
from data_structures.relationships import SelectionInterface
from typing import Dict, Type, Any
from textual.message import Message
from textual.reactive import reactive

from dataclasses import dataclass
"""
TODO: Implement logger

Move interface away

ABSTRACT THINGS
"""


class ConfigurationController(Static):    

    _handler: ConfigurationHandler | None = None
    _selection_interfaces: Dict[str, SelectionInterface] = {}
    _current_selected_object = None

    # Useful wrappers    
    def select_new_dal_from_id(self, new_id: str, new_class: str):
        self._current_selected_object = self.handler.get_obj(new_id, new_class)
    
    @property
    def current_dal(self):
        return self._current_selected_object
    
    @current_dal.setter
    def current_dal(self, new_dal):
        if new_dal!=self._current_selected_object:
            self._current_selected_object=new_dal
            self.post_message(self.Changed(self._current_selected_object))
    
    def save_configuration(self, update_message: str = "Updated config "):
        self._handler.commit(update_message)

    def update_configuration(self, attr_name, update_value):
        try:
            setattr(self._current_selected_object, attr_name, update_value)
            self._handler.configuration.update_dal(self._current_selected_object)
        except:
            raise AttributeError(f"Cannot find attribute {attr_name}")

    def new_handler_from_str(self, file_name: str):
        self._handler = ConfigurationHandler(file_name)

    @property
    def handler(self):
        return self._handler
    
    @handler.setter
    def handler(self, new_handler: ConfigurationHandler):
        self._handler = new_handler
    
    @property
    def configuration(self):
        return self._handler.configuration

    @property
    def interface(self):
        return self._selection_interfaces

    @interface.setter
    def interface(self, selection_handler: Type[SelectionInterface]):
        self.__no_handler_error()
        interface = selection_handler(self._handler)
        self._selection_interfaces[repr(interface)] = interface

    def __no_handler_error(self):
        if self._handler is None:
            raise Exception("No handler has been setup")


    class Changed(Message):
        def __init__(self, dal: object):
            super().__init__()
            self.dal = dal