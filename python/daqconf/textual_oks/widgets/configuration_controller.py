from textual.widgets import Static
from textual.message import Message

from textual_oks.data_structures.configuration_handler import ConfigurationHandler
from textual_oks.data_structures.selection_interface_factory import SelectionInterfaceFactory
from textual_oks.data_structures.selection_interface import SelectionInterface
from typing import Dict

class ConfigurationController(Static):    
    """Controller widget for the full configuration. In principal this is 
    where all communication with the configuration is actually done!
    """
    BINDINGS = [("ctrl+s", "save_configuration", "Save Configuration")]

    _handler: ConfigurationHandler | None = None
    _selection_interfaces: Dict[str, SelectionInterface] = {}
    _current_selected_object = None

    def on_mount(self):
        self._logger = self.app.query_one("RichLogWError")

    # Useful wrappers    
    def select_new_dal_from_id(self, new_id: str, new_class: str):
        """Swap currently selected DAL object via its unique ID and class

        Arguments:
            new_id -- UID of new DAL
            new_class -- Class of DAL
        """        
        self._current_selected_object = self.handler.get_obj(new_id, new_class)
    
    @property
    def current_dal(self):
        """Get current selected dal
        """        
        return self._current_selected_object
    
    @current_dal.setter
    def current_dal(self, new_dal):
        """Set the current dal via a pre-existing dal

        Arguments:
            new_dal -- New dal object
        """        
        if new_dal!=self._current_selected_object:
            self._current_selected_object=new_dal
            self.post_message(self.Changed(self._current_selected_object))
    
    def update_configuration(self, attr_name, update_value):
        """Update an attribute of the currently loaded dal object.
        NOTE This does not update the database file itself

        Arguments:
            attr_name -- Attribute to update
            update_value -- New value for attribute
        """        
        try:
            setattr(self._current_selected_object, attr_name, update_value)
            self._handler.configuration.update_dal(self._current_selected_object)        
        except Exception as _:
            self._logger.write_error(f"Could not update [yellow]{attr_name}[/yellow] to [yellow]{update_value}[/yellow] for {self.generate_rich_string(self._current_selected_object)}")

    def new_handler_from_str(self, file_name: str):
        """Set new handler object by file name

        Arguments:
            file_name -- New database to load
        """ 
        # try:
        self._handler = ConfigurationHandler(file_name)
        # except:
        #     raise Exception(f"Could not open {file_name}")

    @property
    def handler(self)->ConfigurationHandler | None:
        """Return the configuration handler

        Returns:
            ConfigurationHandler instance
        """        
        return self._handler
    
    @handler.setter
    def handler(self, new_handler: ConfigurationHandler):
        """Set new handelr

        Arguments:
            new_handler -- New handler object
        """        
        self._handler = new_handler
    
    @property
    def configuration(self):
        """Return current configuration

        Returns:
            Access the raw configuration
        """        
        return self._handler.configuration

    @classmethod
    def generate_rich_string(cls, dal_obj)->str:
        return f"[yellow]{dal_obj.className()}[/yellow]@[red]{getattr(dal_obj, 'id')}[/red]"


    def get_interface(self):
        """get all interface objects. The interface defines an "ordering" for objects
        in the configuration

        Returns:
            dict{interfaces}
        """        
        return self._selection_interfaces

    def add_interface(self, interface_label: str)->None:
        self.__no_handler_error()
        self._selection_interfaces[interface_label]= \
            SelectionInterfaceFactory.get_interface(interface_label, self._handler)

    # One small shortcut
    def commit_configuration(self, message: str)->None:
        """Save configuration with a message to database
        """        
        self._handler.commit(message)
        self._logger.write(f"[green]Saved configuration with message:[/green] [red]{message}[/red]")

    def rename_dal(self, new_name: str)->None:
        """Rename the currently selected object [NOT TESTED]
        """        
        self._current_selected_object.rename_object(new_name)

    def add_new_conf_obj(self, class_id: str, uid: str):
        """Add new object to configuration
        """        
        self._handler.add_new_conf_obj(class_id, uid)
        self._logger.write(f"[green]Added new configuration object[/green] [red]{class_id}[/red]@[yellow]{uid}[/yellow]")
        
    def destroy_conf_obj(self, class_id: str, uid: str):
        """Destroy object in configuration
        """
        self._handler.destroy_conf_obj(class_id, uid)
        self._logger.write(f"[green]Destroyed configuration object[/green] [red]{class_id}[/red]@[yellow]{uid}[/yellow]")

    def __no_handler_error(self):
        """Raise error if no handler is setup"""
        if self._handler is None:
            raise Exception("No handler has been setup")

    class Changed(Message):
        def __init__(self, dal: object):
            """Notify if/when configuration is changed"""
            super().__init__()
            self.dal = dal