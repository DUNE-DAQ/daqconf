from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Horizontal, Container

from textual_oks.widgets.configuration_controller import ConfigurationController
    
class SaveWithMessage(Static):
    def __init__(self, name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
                
        main_screen = self.app.get_screen("main")
        self._controller = main_screen.query_one(ConfigurationController)

    def compose(self):
        yield Container(
            Horizontal(
                Button("Save", id="save"),
                Button("Cancel", id="cancel"),
                classes="buttons"
            ),
            Input(placeholder="Message goes here", classes="save_message"),
            id = "save_box"
        )
    def save_config(self):
        input = self.query_one(Input)
        message = input.value
        
        self._controller.commit_configuration(message)
        
    def on_input_submitted(self):
        self.save_config()
        self.app.pop_screen()
        
    def on_button_pressed(self, event: Button.Pressed)->None:
        if event.button.id == "save":
            self.save_config()
        
        # Cancel button does this too but no need to check!
        self.app.pop_screen()
            

class SaveWithMessageScreen(ModalScreen):
    CSS_PATH = "../../textual_css/save_menu_layout.tcss"
    
    def __init__(self, name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
                
        main_screen = self.app.get_screen("main")
        self._controller = main_screen.query_one(ConfigurationController)

    def compose(self)->ComposeResult:     
        yield SaveWithMessage()
    
    def on_mount(self) -> None:
        message_box = self.query_one(SaveWithMessage)
        message_box.focus()
        
    