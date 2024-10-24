'''
App for testing configuration 
'''
from os import environ, path
from  daqconf.cider.app_structures.main_screen import MainScreen

# Textual Imports
from textual.app import App

class DbeApp(App):
    # HACK: Need to sort this, only way to get the CSS to work
    css_file_path = f"{environ.get('DAQCONF_SHARE')}/config/textual_dbe/textual_css"

    CSS_PATH = f"{css_file_path}/main_app_layout.tcss"
    SCREENS = {"main": MainScreen}
    
    _input_file_name = None
    
    def set_input_file(self, input_file_name: str):
        self._input_file_name = input_file_name
    
    def on_mount(self):
        self.push_screen("main")
        
        if self._input_file_name is not None:
            self.app.get_screen("main").set_input_file(self._input_file_name)