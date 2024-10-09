from textual.app import ComposeResult
from textual.geometry import Region
from textual.widgets import Static, Button, ContentSwitcher
from textual.containers import Horizontal

from daqconf.textual_dbe.widgets.selection_menu import SelectionMenu


class SelectionPanel(Static):
    """Selection panel structure. Allows user to select between different configuration views
    """    
    
    _current_menu = None
    _saved_states = None
    _menu_ids = {"Sort By Class" : "class-selection",
                    "Sort By Relationship" : "relation-selection"}
    
    def compose(self) -> ComposeResult:
        """Compose the selection panel for use in the app
        """        
        # There has to be a better way of doing this
        
        
        with Horizontal(id="buttons"):
            for label, id in self._menu_ids.items():
                yield Button(label, id=id)
        
        if self._current_menu is None:
            self._current_menu = list(self._menu_ids.values())[0]
        
        if self._saved_states is None:
            self._saved_states = [None]*len(self._menu_ids)
        
        with ContentSwitcher(initial=self._current_menu):
            for i, id in enumerate(self._menu_ids.values()):
                
                menu =  SelectionMenu(id=id)                
                yield menu

    
    # Not fully implemented
    def save_menu_state(self):
        # for i, menu in enumerate(self._menu_ids.values()):
            # selection_menu = self.query_one(f"#{menu}", SelectionMenu)
            # self._saved_states[i] = selection_menu.save_tree_state()
        self._current_menu = self.query_one(ContentSwitcher).current
        
    def restore_menu_state(self):
        # for i, menu in enumerate(self._menu_ids.values()):
        #     selection_menu = self.query_one(f"#{menu}", SelectionMenu)
        #     selection_menu.restore_tree_state(self._saved_states[i])
            
        self.query_one(ContentSwitcher).current = self._current_menu
            
            
    def on_button_pressed(self, event: Button.Pressed)->None:
        """Swap between different configuration views via button. Currently bound here for...reasons
        """        
        self.query_one(ContentSwitcher).current = event.button.id
        # Also swap this around so refreshing is smoother!
