from textual.app import ComposeResult
from textual.widgets import Static, Button, ContentSwitcher
from textual.containers import Horizontal
from textual_oks.widgets.selection_menu import SelectionMenu


class SelectionPanel(Static):
    def compose(self) -> ComposeResult:
        # There has to be a better way of doing this
        menu_ids = {"Sort By Class" : "class-selection",
                    "Sort By Relationship" : "relation-selection"}
        
        with Horizontal(id="buttons"):
            for label, id in menu_ids.items():
                yield Button(label, id=id)
        
        with ContentSwitcher(initial=list(menu_ids.values())[0]):
            for id in menu_ids.values():
                yield SelectionMenu(id=id)
