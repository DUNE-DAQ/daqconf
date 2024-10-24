
from typing import Dict
from os import path, environ

from textual.screen import ModalScreen, Screen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Horizontal, Container

from daqconf.cider.widgets.configuration_controller import ConfigurationController
from daqconf.cider.widgets.config_table import ConfigTable
from daqconf.cider.app_structures.selection_panel import SelectionPanel
from daqconf.cider.widgets.popups.directory_tree import DatabaseDirectoryTree

class __MenuWithButtons(Static):
    def __init__(self, button_labels: Dict[str, str], name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        """Base class for popups with N buttons and a single input field
        """        

        self._button_labels = button_labels
        self._main_screen = self.app.get_screen("main")
        self._config_controller = self._main_screen.query_one(ConfigurationController)

    def compose(self):
        """Generates interfaxce
        """
        with Container(id="save_box"):
            with Horizontal(classes="buttons"):
                # Add buttons
                for button_id, button_text in self._button_labels.items():
                    yield Button(button_text, id=button_id)
                yield Button("Cancel", id="cancel")
            # Add input field
            yield Input(placeholder="Message goes here", classes="save_message")
        
    def button_actions(self, button_id: str| None):
        raise NotImplementedError("button_actions should be implemented in the child class")
        
    def input_action(self, message: str):
        raise NotImplementedError("input_action should be implemented in the child class")
            
    def on_input_submitted(self, event):
        if event.value:        
            self.input_action(event.value)
            self.app.screen.dismiss(result="yay")
        
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id != "cancel":
            self.button_actions(event.button.id)
        
        # Cancel button does this too but no need to check!
        self.app.screen.dismiss(result="yay")
        


class SaveWithMessage(__MenuWithButtons):
    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        """
        Concrete class for saving configuration with a message
        """
        self._button_labels = {
            "save" : "Save"
        }
        
        super().__init__(self._button_labels, name, id, classes)

    def input_action(self, message: str):
        self._config_controller.commit_configuration(message)
    
    def button_actions(self, button_id: str):
        match button_id:
             case "save":
                input = self.query_one(Input)
                self.input_action(input.value)
                 
class SaveWithMessageScreen(ModalScreen[bool]):
    css_file_path = f"{environ.get('DAQCONF_SHARE')}/config/textual_dbe/textual_css"
    
    CSS_PATH = f"{css_file_path}/save_menu_layout.tcss"
    """
    Splash screen for saving to file
    """
                    
    def compose(self)->ComposeResult:     
        yield SaveWithMessage()
    
    def on_mount(self) -> None:
        message_box = self.query_one(SaveWithMessage)
        message_box.focus()
        
class OpenFile(__MenuWithButtons):
    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        
        self._button_labels = {
            "open" : "Open",
            "browse" : "Browse"
        }
        """
        Concrete class for opening a configuration file
        """
        
        super().__init__(self._button_labels, name, id, classes)


    def input_action(self, new_config: str):
        """
        Add new handler based on config name
        """
        try:
            self._main_screen.update_with_new_input(new_config)        
        except:
            logger = self._main_screen.query_one("RichLogWError")
            logger.write_error(f"[red]Could open: {new_config}")
    
    def button_actions(self, button_id: str | None):
        """Open file or browse for file (not implemented)

        Arguments:
            button_id -- Button label
        """        
        match button_id:
            case "open":
                input = self.query_one(Input)
                
                # Safety check to avoid empty input
                if input:                
                    self.input_action(input.value)

            case "browse":
                logger = self._main_screen.query_one("RichLogWError")
                logger.write_error("Sorry not done this yet, please enter full file path and hit enter/open!")


class OpenFileScreen(Screen):
    
    # HACKY WAY TO GET THE CSS TO WORK
    css_file_path = f"{environ.get('DAQCONF_SHARE')}/config/textual_dbe/textual_css"
    
    CSS_PATH = f"{css_file_path}/save_menu_layout.tcss"
    
    def __init__(self, name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        """Add in configuration screen
        """        
        super().__init__(name=name, id=id, classes=classes)
        main_screen = self.app.get_screen("main")
        self._controller = main_screen.query_one(ConfigurationController)
        
        
    def compose(self)->ComposeResult:
        yield OpenFile()
        
    def on_mount(self) -> None:
        message_box = self.query_one(OpenFile)
        message_box.focus()
        
        
