from textual import on
from textual.screen import Screen
from textual.widgets import Input, Select, Button, Static

from daqconf.cider.widgets.config_table import ConfigTable
from daqconf.cider.widgets.configuration_controller import ConfigurationController

"""
Collection of objects that define the configuration object
"""

class ConfigObjectSelectionPanel(Static):
    """Configurable object selection panel"""

    def Compose(self):
        """Compose the app            
        """        
        main_screen = self.app.get_screen("main")
        self._controller: ConfigurationController = main_screen.query_one(ConfigurationController)

        if self._controller.handler is None:
            raise Exception("Configuration handler not found")

        yield Input(placeholder="Enter new object name", id="new_object_name")
        yield Select.from_values(list(self._controller.handler.configuration_handler.get_all_conf_classes().keys()), id="new_object_class")
        yield Button("Select", id="select_object")

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        pass
