'''
App for testing configuration 
'''

from interface.config_table import ConfigTable
from interface.selection_menu import SelectionMenu
from data_structures.controller import ConfigurationController
from data_structures.relationships import ClassSelectionMenu, RelationalSelectionMenu
from textual.containers import Horizontal, VerticalScroll

from textual.app import App
from textual.screen import Screen
from textual.widgets import Header,Footer, ContentSwitcher, Button



class MainScreen(Screen):
    def compose(self):
        # Import for app control
        config_controller = ConfigurationController()
        config_controller.new_handler_from_str(file_name="/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/test_case_2/test-session.data.xml")
        config_controller.interface = RelationalSelectionMenu
        config_controller.interface = ClassSelectionMenu

        yield config_controller

        self._class_menu = SelectionMenu(id="class_menu")
        self._class_menu.interface_label = "ClassSelectionMenu"
        self._relational_menu = SelectionMenu(id = "relational_menu")
        self._relational_menu.interface_label="RelationalSelectionMenu"
        
        with Horizontal(id="buttons"):
            yield Button("By Class", id="class_menu")
            yield Button("By Relation", id="relational_menu")
        
        with ContentSwitcher(initial="class_menu"):
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
    CSS_PATH = "content_switcher.tcss"
    
    def on_mount(self):        
        self.push_screen("main")
    