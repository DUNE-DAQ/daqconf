'''
Table for displaying DAL information
'''
from textual.widgets import Static, DataTable
from textual.reactive import reactive
from textual_oks.widgets.popups.edit_cell_screen import EditCellScreen

from textual_oks.widgets.configuration_controller import ConfigurationController

class ConfigTable(Static):
    __COLS = reactive([("Attribute", "Value", "Type", "Is Multivalue"), ("", "","","")])
    _data_table = DataTable()
    
    def on_mount(self):
        self._controller: ConfigurationController = self.app.query_one("ConfigurationController") #type: ignore

        for col in self.__COLS[0]:

            width = 23
            if col=="Value":
                width = 60

            self._data_table.add_column(col, width=width, key=col)
        
        self._data_table.add_rows(self.__COLS[1:])
        
        self._data_table.fixed_rows = 0
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
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(EditCellScreen(event))

