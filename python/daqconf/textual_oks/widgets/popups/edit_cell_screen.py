from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Input

from typing import Any

from textual_oks.widgets.configuration_controller import ConfigurationController

class EditCellScreen(ModalScreen):
    def __init__(
        self, event: Any, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        """Screen which pops up when a cell is clicked in the ConfigTable
        """
        
        # Need to get the main screen configuration
        main_screen = self.app.get_screen("main")
        self._data_table  = main_screen.query_one("DataTable")
        self._config_table = main_screen.query_one("ConfigTable")
        # self._config_table = main_screen.query_one("ConfigTable")

        # Get necessary info from table
        self._row_key = event.row_key
        self._current_row = self._data_table.get_row(event.row_key)
        self._controller = main_screen.query_one(ConfigurationController)

    def compose(self) -> ComposeResult:
        yield Input()

    def on_mount(self) -> None:
        """Finds the cell that was clicked and populates the input field
        """        
        cell_input = self.query_one(Input)
        # Harcoded...
        cell_input.value = str(self._current_row[1])
        cell_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Applies update to the configuration object

        Arguments:
            event -- Information from table row
        """        
        attr_name     = self._current_row[0]
        update_value  = event.value
        attr_type     = self._current_row[2]
        is_multivalue = self._current_row[3]  

        # Need to properly cast to list        
        if is_multivalue: 
            update_value=self.process_multivalue_input(update_value, attr_type)
        else:
            update_value = self.cast_to_type_by_str(update_value, attr_type)
        
        self._controller.update_configuration(attr_name, update_value)        
        self._config_table.update_table(self._controller.current_dal)

        self.app.pop_screen()

    
    @classmethod
    def cast_to_type_by_str(cls, input_variable: str, data_type: str):
        """Attempt to enforce type-checking/convertion on input variable based on type-name in table. Will not work for non-built-in types
        """        
        try:
            return getattr(__builtins__, data_type)(input_variable)
        except:
            return input_variable
        
    @classmethod
    def process_multivalue_input(cls, input_value: str, data_type: str):
        """Processing required to ensure multi-variate objects are correctly placed in the table

        """        
        # Strip brackets
        input_value = input_value.replace("[", "")
        input_value = input_value.replace("]", "")
        # Strip space
        input_value = input_value.replace(" ", "")
        input_value = [cls.cast_to_type_by_str(i, data_type) for i in input_value.split(",")]

        return input_value
