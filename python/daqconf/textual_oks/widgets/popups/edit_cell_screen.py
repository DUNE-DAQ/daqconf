from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Input

from textual_oks.widgets.configuration_controller import ConfigurationController

from typing import Any

class EditCellScreen(ModalScreen):
    def __init__(
        self, event: Any, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        
        
        main_screen = self.app.get_screen("main")
        self._data_table  = main_screen.query_one("DataTable")
        self._config_table = main_screen.query_one("ConfigTable")
        # self._config_table = main_screen.query_one("ConfigTable")

        # Get necessary info
        self._row_key = event.row_key
        self._current_row = self._data_table.get_row(event.row_key)
        self._controller = main_screen.query_one(ConfigurationController)

    def compose(self) -> ComposeResult:
        yield Input()

    def on_mount(self) -> None:
        cell_input = self.query_one(Input)
        # Harcoded...
        cell_input.value = str(self._current_row[1])
        cell_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
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
        try:
            return getattr(__builtins__, data_type)(input_variable)
        except:
            return input_variable
        
    @classmethod
    def process_multivalue_input(cls, input_value: str, data_type: str):
        # Strip brackets
        input_value = input_value.replace("[", "")
        input_value = input_value.replace("]", "")
        # Strip space
        input_value = input_value.replace(" ", "")
        input_value = [cls.cast_to_type_by_str(i, data_type) for i in input_value.split(",")]

        return input_value
