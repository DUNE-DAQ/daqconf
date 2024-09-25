'''
App for testing configuration 
'''

from textual_oks.widgets.config_table import ConfigTable
from textual_oks.widgets.configuration_controller import ConfigurationController
from textual_oks.widgets.popups.save_menu import SaveWithMessageScreen

from textual_oks.app_structures.selection_panel import SelectionPanel

from textual.app import App
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Button, Footer
from textual_oks.widgets.custom_rich_log import RichLogWError


from textual import events

class MainScreen(Screen):

    BINDINGS = [("ctrl+s", "save_configuration", "Save Configuration"),
                ("S", "save_configuration_with_message", "Save Configuration with Message")]
    
    def compose(self):
        # Import for app control
        config_controller = ConfigurationController()
        config_controller.new_handler_from_str(file_name="/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/test_case_2_copy/test-session.data.xml")
        config_controller.add_interface("class-selection")
        config_controller.add_interface("relation-selection")
        yield config_controller

        self._config_table= ConfigTable(id="main_table")
        yield self._config_table
        yield SelectionPanel()
        yield RichLogWError(id="main_log", highlight=True, markup=True)
        # yield Header()
        yield Footer()
        
    def on_button_pressed(self, event: Button.Pressed)->None:
        self.query_one(ContentSwitcher).current = event.button.id
        
    def on_configuration_controller_changed(self, event):
        self._config_table.update_table(event.dal)
        
    def action_save_configuration(self)->None:
        config = self.query_one(ConfigurationController)
        config.commit_configuration("Update configuration")

    def action_save_configuration_with_message(self)->None:
        self.app.push_screen(SaveWithMessageScreen())

class TestApp(App):
    CSS_PATH = "../textual_css/dummy_layout.tcss"

    SCREENS = {"main": MainScreen}
    
    def on_mount(self):        
        self.push_screen("main")
    