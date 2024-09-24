'''
App for testing configuration 
'''

from textual_oks.interface.config_table import ConfigTable
from textual_oks.interface.selection_menu import SelectionMenu
from textual_oks.data_structures.configuration_controller import ConfigurationController
from textual_oks.data_structures.selection_interface import ClassSelectionMenu, RelationalSelectionMenu
from textual.containers import Horizontal, VerticalScroll

from textual.app import App
from textual.screen import Screen
from textual.widgets import Header,Footer, ContentSwitcher, Button



class MainScreen(Screen):
    def compose(self):
        # Import for app control
        config_controller = ConfigurationController()
        config_controller.new_handler_from_str(file_name="/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/test_case_2/test-session.data.xml")
        config_controller.add_interface("class-selection")
        config_controller.add_interface("relation-selection")
        yield config_controller

        self._class_menu = SelectionMenu(id="class-selection")
        self._relational_menu = SelectionMenu(id = "relation-selection")
        
        with Horizontal(id="buttons"):
            yield Button("By Class", id="class-selection")
            yield Button("By Relation", id="relation-selection")
        
        with ContentSwitcher(initial="class-selection"):
            yield self._class_menu
            yield self._relational_menu            

        self._config_table= ConfigTable(id="main_table")
        yield self._config_table
        # yield Header()
        # yield Footer()
        
    def on_button_pressed(self, event: Button.Pressed)->None:
        self.query_one(ContentSwitcher).current = event.button.id
        
    def on_configuration_controller_changed(self, event):
        self._config_table.update_table(event.dal)

class TestApp(App):
    SCREENS = {"main": MainScreen}
    CSS_PATH = "dummy_layout.tcss"
    
    def on_mount(self):        
        self.push_screen("main")
    