'''
Table for displaying DAL information
'''
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Input
from textual.reactive import reactive
from textual.screen import ModalScreen

from typing import Any

from data_structures.controller import ConfigurationController

class ConfigTable(Static):
    __COLS = reactive([("Attribute", "Value", "Type"), ("", "","")])
    _data_table = DataTable()
    
    def on_mount(self):
        self._controller: ConfigurationController = self.app.query_one("ConfigurationController") #type: ignore

        self._data_table.add_columns(*self.__COLS[0])
        self._data_table.add_rows(self.__COLS[1:])
        
        self._data_table.fixed_rows = 0
        self._data_table.zebra_stripes=True
    
    def compose(self):
        yield self._data_table
    
    def update_table(self, config_instance):
        
        self._data_table.clear()
        
        # Get attributes
        attributes = self._controller.configuration.attributes(config_instance.className(), True)
        
        for a in attributes:
            attr = getattr(config_instance, a)
            if attr=='':
                self._data_table.add_row(a, "None", "None")
            else:
                self._data_table.add_row(a, attr, type(attr))
                
    @property
    def data_table(self)->DataTable:
        return self._data_table
    
    def on_configuration_controller_changed(self, event: ConfigurationController.Changed):
        raise Exception("hello")
        self.update_table(event.dal)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:

        cell_value: Any = event.value
        if event.coordinate.column!=1:
            return

        self.app.push_screen(EditCellScreen(cell_value))

class EditCellScreen(ModalScreen):
    def __init__(
        self,
        cell_value: Any,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.cell_value = cell_value

    def compose(self) -> ComposeResult:
        yield Input()

    def on_mount(self) -> None:
        cell_input = self.query_one(Input)
        cell_input.value = str(self.cell_value)
        cell_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        main_screen = self.app.get_screen("main")

        table = main_screen.query_one(DataTable)
        table.update_cell_at(
            table.cursor_coordinate,
            event.value,
            update_width=True,
        )

        config_table = main_screen.query_one(ConfigTable)
        attr_name    = config_table.data_table.get_cell_at((config_table.data_table.cursor_coordinate.row, 0))
        update_value = event.value

        controller = main_screen.query_one(ConfigurationController)
        
        controller.update_configuration(attr_name, update_value)        

        self.app.pop_screen()