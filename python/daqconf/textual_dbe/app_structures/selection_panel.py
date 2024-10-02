from textual.app import ComposeResult
from textual.geometry import Region
from textual.widgets import Static, Button, ContentSwitcher
from textual.containers import Horizontal
from textual_dbe.widgets.selection_menu import SelectionMenu


class SelectionPanel(Static):
    """Selection panel structure. Allows user to select between different configuration views
    """    
    def compose(self) -> ComposeResult:
        """Compose the selection panel for use in the app
        """        
        # There has to be a better way of doing this
        menu_ids = {"Sort By Class" : "class-selection",
                    "Sort By Relationship" : "relation-selection"}
        
        with Horizontal(id="buttons"):
            for label, id in menu_ids.items():
                yield Button(label, id=id)
        
        with ContentSwitcher(initial=list(menu_ids.values())[0]):
            for id in menu_ids.values():
                yield SelectionMenu(id=id)
                
        def on_button_pressed(self, event: Button.Pressed)->None:
            """Swap between different configuration views via button. Currently bound here for...reasons
            """        
            self.query_one(ContentSwitcher).current = event.button.id