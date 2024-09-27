'''
App for testing configuration 
'''

from textual_oks.widgets.config_table import ConfigTable
from textual_oks.widgets.configuration_controller import ConfigurationController
from textual_oks.widgets.popups.file_io import SaveWithMessageScreen, OpenFileScreen

from textual_oks.app_structures.selection_panel import SelectionPanel

from textual.app import App
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Button, Header, Footer, Placeholder
from textual_oks.widgets.custom_rich_log import RichLogWError
from textual.events import ScreenSuspend

class MainScreen(Screen):

    BINDINGS = [("ctrl+s", "save_configuration", "Save Configuration"),
                ("S", "save_configuration_with_message", "Save Configuration with Message"),
                ("o", "open_configuration", "Open Configuration"),
                ("a", "add_configuration", "Add Configuration"),
                ("d", "destroy_configuration", "Destroy Configuration")]
    
    def compose(self):
        # Import for app control
        self._config_controller = ConfigurationController()
        yield self._config_controller
        yield Footer()
        
        yield RichLogWError(id="main_log", highlight=True, markup=True)

        
    def on_button_pressed(self, event: Button.Pressed)->None:
        self.query_one(ContentSwitcher).current = event.button.id
        
    def on_configuration_controller_changed(self, event):
        config_table = self.query_one(ConfigTable)
        if config_table is not None:
            config_table.update_table(event.dal)
        
    def action_save_configuration(self)->None:
        config = self.query_one(ConfigurationController)
        config.commit_configuration("Update configuration")

    def action_save_configuration_with_message(self)->None:
        self.app.push_screen(SaveWithMessageScreen())
        
    async def action_open_configuration(self) -> None:
        # Push the OpenFileScreen and wait for it to be closed
        await self.app.push_screen(OpenFileScreen())

    async def action_add_configuration(self)->None:
        try:
            self._config_controller.add_new_conf_obj("GeoId", "dummy")
            menu = self.query_one(SelectionPanel)
            menu.refresh(recompose=True)
            
        except:
            self.query_one(RichLogWError).write_error(f"Could not add configuration object")
    
    async def action_destroy_configuration(self)->None:
        # try:
            self._config_controller.destroy_conf_obj("GeoId", "dummy")
            menu = self.query_one(SelectionPanel)
            menu.refresh(recompose=True)
        # except:
        #     self.query_one(RichLogWError).write_error("Could not destroy configuration object")

class TestApp(App):
    CSS_PATH = "../textual_css/dummy_layout.tcss"
    SCREENS = {"main": MainScreen}
    
    def on_mount(self):        
        self.push_screen("main")
    