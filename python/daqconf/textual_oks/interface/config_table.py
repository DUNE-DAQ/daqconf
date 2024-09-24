'''
Table for displaying DAL information
'''
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Input
from textual.reactive import reactive
from textual.screen import ModalScreen

from typing import Any

from textual_oks.data_structures.configuration_controller import ConfigurationController

class ConfigTable(Static):
    __COLS = reactive([("Attribute", "Value", "Type", "Is Multivalue"), ("", "","")])
    _data_table = DataTable()
    
    def on_mount(self):
        self._controller: ConfigurationController = self.app.query_one("ConfigurationController") #type: ignore

        self._data_table.add_columns(*self.__COLS[0])
        self._data_table.add_rows(self.__COLS[1:])
        
        self._data_table.fixed_rows = 0
        self._data_table.fixed_width = True
        self._data_table.cursor_type = "row"
        self._data_table.zebra_stripes=True
    
    def compose(self):
        yield self._data_table
    
    def update_table(self, config_instance):
        
        self._data_table.clear()
        
        # Get attributes
        attributes = self._controller.configuration.attributes(config_instance.className(), True)
        
        for attr_name, attr_properties in attributes.items():
            attr_val = getattr(config_instance, attr_name)
            if attr_val=='':
                attr_val = attr_properties['init-value']
            else:
                self._data_table.add_row(attr_name, attr_val, attr_properties['type'], attr_properties['multivalue'])
                
    @property
    def data_table(self)->DataTable:
        return self._data_table
    
    def on_configuration_controller_changed(self, event: ConfigurationController.Changed):
        raise Exception("hello")
        self.update_table(event.dal)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(EditCellScreen(event))

class EditCellScreen(ModalScreen):
    def __init__(
        self,
        event: Any,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
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
