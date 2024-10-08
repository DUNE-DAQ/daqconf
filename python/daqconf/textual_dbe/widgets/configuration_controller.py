import confmodel

from typing import Dict

from textual.widgets import Static
from textual.message import Message

from daqconf.textual_dbe.data_structures.structured_configuration import StructuredConfiguration
from daqconf.textual_dbe.data_structures.configuration_handler import ConfigurationHandler
from daqconf.textual_dbe.data_structures.selection_interface_factory import SelectionInterfaceFactory
from daqconf.textual_dbe.data_structures.selection_interface import SelectionInterface

class ConfigurationController(Static):    
    """Controller widget for the full configuration. In principal this is 
    where all communication with the configuration is actually done!
    """
    BINDINGS = [("ctrl+s", "save_configuration", "Save Configuration")]

    _handler: StructuredConfiguration | None = None
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
        if self.handler is not None:
            self._current_selected_object = self.handler.configuration_handler.get_obj(new_id, new_class)
    
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
        if self.handler is None:
            self._logger.write_error("No handler has been setup")

        
        try:
            setattr(self._current_selected_object, attr_name, update_value)
            self._handler.configuration_handler.configuration.update_dal(self._current_selected_object)        
        except Exception as _:
            self._logger.write_error(f"Could not update [yellow]{attr_name}[/yellow] to [yellow]{update_value}[/yellow] for {self.generate_rich_string(self._current_selected_object)}")

    def new_handler_from_str(self, file_name: str):
        """Set new handler object by file name

        Arguments:
            file_name -- New database to load
        """ 
        # try:
        self._handler = StructuredConfiguration(file_name)
        # except:
        #     raise Exception(f"Could not open {file_name}")

    @property
    def handler(self)->StructuredConfiguration | None:
        """Return the configuration handler

        Returns:
            ConfigurationHandler instance
        """        
        return self._handler
    
    @handler.setter
    def handler(self, new_handler: StructuredConfiguration):
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
        self.__no_handler_error()
        
        return self._handler.configuration_handler.configuration

    @classmethod
    def generate_rich_string(cls, dal_obj, obj_disabled: bool=False)->str:
        """Generate a rich string for a DAL object, shouldn't live here but :shrug:"""
        if obj_disabled:
            return f"[grey]{getattr(dal_obj, 'id')}[/grey]@[grey]{dal_obj.className()}[/grey]"
        else:
            return f"[yellow]{getattr(dal_obj, 'id')}[/yellow]@[red]{dal_obj.className()}[/red]"


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
        self._handler.configuration_handler.commit(message)
        self._logger.write(f"[green]Saved configuration with message:[/green] [red]{message}[/red]")

    def rename_dal(self, new_name: str)->None:
        """Rename the currently selected object [NOT TESTED]
        """        
        self._current_selected_object.rename_object(new_name)

    def add_new_conf_obj(self, class_id: str, uid: str):
        """Add new object to configuration
        """        
        self._handler.configuration_handler.add_new_conf_obj(class_id, uid)
        self._logger.write(f"[green]Added new configuration object[/green] [red]{class_id}[/red]@[yellow]{uid}[/yellow]")
        
    def destroy_conf_obj(self, class_id: str, uid: str):
        """Destroy object in configuration
        """
        self._handler.configuration_handler.destroy_conf_obj(class_id, uid)
        self._logger.write(f"[green]Destroyed configuration object[/green] [red]{class_id}[/red]@[yellow]{uid}[/yellow]")


    def toggle_disable_conf_obj(self):
        """Disable current object in configuration
        """
        if self._current_selected_object not in self._handler.configuration_handler.get_all_conf_classes()['Component']:
            self._logger.write_error(f"Cannot disable {self.generate_rich_string(self._current_selected_object)} must inherit from [red]Component[/red]!")
            return
        
        self._logger.write(f"[bold red]Warning this will toggle whether[/bold red] {self.generate_rich_string(self._current_selected_object)} [bold red] is enabled/disabled in ALL sessions loaded")
        self._logger.write("[bold red]PLEASE USE WITH CAUTION![/bold red]")

        
        # Get all top level sessions
        top_sessions = [top_object for top_object in self._handler.relational_graph.top_level_nodes\
                            if top_object.className() == "Session"]
        
        # DAL as configuration object        
        # Loop over all sessions
        for session in top_sessions:
            session_disabled_elements = session.disabled
            disabled = self._current_selected_object in session_disabled_elements

            if disabled:
                self._logger.write(f"Enabling {self.generate_rich_string(self._current_selected_object)} in {self.generate_rich_string(session)}")
                session_disabled_elements.remove(self._current_selected_object)
            else:
                self._logger.write(f"Disabling {self.generate_rich_string(self._current_selected_object)} in {self.generate_rich_string(session)}")
                session_disabled_elements.append(self._current_selected_object)
                
            session.disabled = session_disabled_elements
            self._handler.configuration_handler.configuration.update_dal(session)        


    def __no_handler_error(self):
        """Raise error if no handler is setup"""
        if self._handler.configuration_handler is None:
            raise Exception("No handler has been setup")

    class Changed(Message):
        def __init__(self, dal: object):
            """Notify if/when configuration is changed"""
            super().__init__()
            self.dal = dal