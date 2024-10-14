from os import environ

from textual.widgets import Static, SelectionList, Button
from textual.widgets.selection_list import Selection
from textual.screen import ModalScreen


from daqconf.textual_dbe.widgets.configuration_controller import ConfigurationController

class SelectSystem(Static):
    def compose(self):
        
        self._configuration_controller = self.app.get_screen("main").query_one(ConfigurationController)
        self._systems =  self._configuration_controller.get_all_systems()
        is_enabled = self._configuration_controller.is_selected_object_enabled()
        
        selections = [Selection(self._configuration_controller.generate_rich_string(s), s, d) for s, d in zip(self._systems, is_enabled)]
        
        selection_list =  SelectionList(*selections, id="system_select_list")
        selection_list.border_title = "Select Systems to toggle object on/off in"
        
        yield selection_list
        yield Button("Apply", id="apply")
        yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed):
                
        if event.button.id == "apply":
            selection_list = self.query_one("#system_select_list").selected

            # Hacky but ensures we know what we are toggling on/off
            selected_systems = [(s, s in selection_list) for s in self._systems]

            self._configuration_controller.toggle_disable_conf_obj(selected_systems)

        menu = self.app.get_screen("main").query_one("SelectionPanel")
        menu.save_menu_state()
        menu.refresh(recompose=True)
        menu.restore_menu_state()

        self.app.screen.dismiss(result="cancel")
        

class SelectSystemScreen(ModalScreen):
    # css_file_path = f"{environ.get('DBT_AREA_ROOT')}/sourcecode/daqconf/python/daqconf/textual_dbe/textual_css"
    # CSS_PATH = f"{css_file_path}/system_selection_layout.tcss"

    def compose(self):
        yield SelectSystem()
        
    def on_mount(self)->None:
        self.query_one(SelectSystem).focus()