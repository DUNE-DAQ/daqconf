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
from textual.containers import Vertical, Horizontal
from textual.binding import Binding


# Custom menu class that creates buttons for each key binding
class ShortcutMenu(Vertical):
    def compose(self):
        # Create a button for each binding in the app's BINDINGS list
        self._screen = self.app.get_screen("main")
        for binding in self._screen.BINDINGS:
            yield Button(binding.description, id=binding.action)  # Button label is the description, ID is the action

    async def on_button_pressed(self, message):
        # Handle button press to trigger the corresponding action
        action = message.button.id  # Get the action from the button's ID
        await self._screen.run_action(action)  # Call the action in the app



class MainScreen(Screen):

    BINDINGS = [
                Binding("ctrl+s", "save_configuration", "Save Configuration"),
                Binding("S", "save_configuration_with_message", "Save Configuration with Message"),
                Binding("o", "open_configuration", "Open Configuration"),
                Binding("a", "add_configuration", "Add Configuration"),
                Binding("d", "destroy_configuration", "Destroy Configuration"),
                Binding("m", "toggle_menu", "Toggle Menu")]
    
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
  
    async def action_toggle_menu(self):
            # Toggle visibility of the menu
            if hasattr(self, "menu"):
                await self.menu.remove()
                del self.menu
            else:
                self.menu = ShortcutMenu()
                await self.mount(self.menu)


class TestApp(App):
    CSS_PATH = "../textual_css/dummy_layout.tcss"
    SCREENS = {"main": MainScreen}
    
    def on_mount(self):        
        self.push_screen("main")
    