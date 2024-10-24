from os import environ

from textual.widgets import Static, SelectionList, Button
from textual.widgets.selection_list import Selection
from textual.screen import ModalScreen


from daqconf.cider.widgets.configuration_controller import ConfigurationController

class SelectSession(Static):
    def compose(self):
        
        self._configuration_controller = self.app.get_screen("main").query_one(ConfigurationController)
        self._sessions =  self._configuration_controller.get_all_sessions()
        is_enabled = self._configuration_controller.is_selected_object_enabled()
        
        selections = [Selection(self._configuration_controller.generate_rich_string(s), s, d) for s, d in zip(self._sessions, is_enabled)]
        
        selection_list =  SelectionList(*selections, id="session_select_list")
        selection_list.border_title = "Select Sessions to toggle object on/off in"
        
        yield selection_list
        yield Button("Apply", id="apply")
        yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed):
                
        if event.button.id == "apply":
            selection_list = self.query_one("#session_select_list").selected

            # Hacky but ensures we know what we are toggling on/off
            selected_sessions = [(s, s in selection_list) for s in self._sessions]

            self._configuration_controller.toggle_disable_conf_obj(selected_sessions)

        menu = self.app.get_screen("main").query_one("SelectionPanel")
        menu.save_menu_state()
        menu.refresh(recompose=True)
        menu.restore_menu_state()

        self.app.screen.dismiss(result="cancel")
        

class SelectSessionScreen(ModalScreen):
    # css_file_path = f"{environ.get('DBT_AREA_ROOT')}/sourcecode/daqconf/python/daqconf/textual_dbe/textual_css"
    # CSS_PATH = f"{css_file_path}/session_selection_layout.tcss"

    def compose(self):
        yield SelectSession()
        
    def on_mount(self)->None:
        self.query_one(SelectSession).focus()