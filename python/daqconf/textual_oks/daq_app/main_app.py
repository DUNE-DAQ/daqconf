'''
App for testing configuration 
'''

from textual_oks.interface.config_table import ConfigTable
from textual_oks.interface.selection_menu import SelectionMenu
from textual_oks.data_structures.configuration_controller import ConfigurationController

from textual_oks.app_structures.selection_panel import SelectionPanel

from textual.app import App
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Button
from textual.containers import Horizontal



class MainScreen(Screen):

    def compose(self):
        # Import for app control
        config_controller = ConfigurationController()
        config_controller.new_handler_from_str(file_name="/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/test_case_2/test-session.data.xml")
        config_controller.add_interface("class-selection")
        config_controller.add_interface("relation-selection")
        yield config_controller

        self._config_table= ConfigTable(id="main_table")
        yield self._config_table
        yield SelectionPanel()
        # yield Header()
        # yield Footer()
        
    def on_button_pressed(self, event: Button.Pressed)->None:
        self.query_one(ContentSwitcher).current = event.button.id
        
    def on_configuration_controller_changed(self, event):
        self._config_table.update_table(event.dal)

class TestApp(App):
    CSS_PATH = "dummy_layout.tcss"

    SCREENS = {"main": MainScreen}
    CSS_PATH = "dummy_layout.tcss"
    
    def on_mount(self):        
        self.push_screen("main")
    