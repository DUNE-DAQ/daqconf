from textual.screen import ModalScreen, Screen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Horizontal, Container

from textual_oks.widgets.configuration_controller import ConfigurationController
from textual_oks.widgets.config_table import ConfigTable
from textual_oks.app_structures.selection_panel import SelectionPanel
from textual_oks.widgets.popups.directory_tree import DatabaseDirectoryTree

from typing import Dict

from os import path

class __MenuWithButtons(Static):
    def __init__(self, button_labels: Dict[str, str], name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)

        self._button_labels = button_labels
        self._main_screen = self.app.get_screen("main")
        self._config_controller = self._main_screen.query_one(ConfigurationController)

    def compose(self):
        with Container(id="save_box"):
            with Horizontal(classes="buttons"):
                # Add buttons
                for button_id, button_text in self._button_labels.items():
                    yield Button(button_text, id=button_id)
                yield Button("Cancel", id="cancel")
            
            yield Input(placeholder="Message goes here", classes="save_message")
        
    def button_actions(self, button_id: str| None):
        pass
    
    def input_action(self, message: str):
        pass
            
    def on_input_submitted(self, event):
        self.input_action(event.value)
        self.app.screen.dismiss(result="yay")
        
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id != "cancel":
            self.button_actions(event.button.id)
        
        # Cancel button does this too but no need to check!
        self.app.screen.dismiss(result="yay")
        


class SaveWithMessage(__MenuWithButtons):
    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        
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
    CSS_PATH = "../../textual_css/save_menu_layout.tcss"
    
    def __init__(self, name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
                
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
        
        super().__init__(self._button_labels, name, id, classes)


    def input_action(self, new_config: str):
        self._config_controller.new_handler_from_str(new_config)
        self.update_main_screen()
    
    def button_actions(self, button_id: str | None):
        match button_id:
            case "open":
                input = self.query_one(Input)
                self.input_action(input.value)

            case "browse":
                raise NotImplementedError("Sorry not done this yet!")

        

    def update_main_screen(self):
        
        self._config_controller.add_interface("class-selection")
        self._config_controller.add_interface("relation-selection")

        try:
            self._main_screen.mount(SelectionPanel())
        except:
            pass    
        try:
            config_table = self._main_screen.query_one(ConfigTable)
            config_table.update_table(self._config_controller.current_dal)
        except:
            config_table = ConfigTable(id="main_table")
            self._main_screen.mount(config_table)

        self._main_screen.refresh()
        
        
        logger = self._main_screen.query_one("RichLogWError")
        
        current_database_path = self._config_controller.configuration.databases[0]
        data_base_name = path.basename(current_database_path)
        
        logger.write(f"[green]Opened new configuration file: [/green][red]{data_base_name}[/red][green].\nConnected databases are:[/green]\n" \
                     + "".join([f"   - [red]{db}[/red] \n" for db in self._config_controller.configuration.get_includes()]))
        

class OpenFileScreen(Screen):
    CSS_PATH = "../../textual_css/save_menu_layout.tcss"
    
    def __init__(self, name: str | None=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        main_screen = self.app.get_screen("main")
        self._controller = main_screen.query_one(ConfigurationController)
        
        
    def compose(self)->ComposeResult:
        yield OpenFile()
        
    def on_mount(self) -> None:
        message_box = self.query_one(OpenFile)
        message_box.focus()
        
        
