'''
Table for displaying DAL information
'''
from textual.widgets import Static, DataTable
from textual.reactive import reactive

from daqconf.cider.widgets.popups.edit_cell_screen import EditCellScreen
from daqconf.cider.widgets.configuration_controller import ConfigurationController

class ConfigTable(Static):
    
    # Columns in table
    __COLS = reactive([("Attribute", "Value", "Type", "Is Multivalue"), ("", "","","")])
    # Empty data table
    _data_table = DataTable()
    
    def on_mount(self):
        """Initialise the table object
        """
        
        # Grab main controller object
        main_screen = self.app.get_screen("main")
        self._controller: ConfigurationController = main_screen.query_one("ConfigurationController") #type: ignore

        # Add default columns
        for col in self.__COLS[0]:

            width = 23
            if col=="Value":
                width = 60

            self._data_table.add_column(col, width=width, key=col)
        
        # Add dummy rows
        self._data_table.add_rows(self.__COLS[1:])
        
        # Some configuration to make it look "nice"
        self._data_table.fixed_rows = 0
        self._data_table.cursor_type = "row"
        self._data_table.zebra_stripes=True
    
    def compose(self):
        yield self._data_table
    
    def update_table(self, config_instance):
        """Updates table to display currently selected configuration object

        Arguments:
            config_instance -- DAL configuration object
        """
        
        # Need to clear the table first
        self._data_table.clear()
        
        # Get attributes for DAL
        attributes = self._controller.configuration.attributes(config_instance.className(), True)
        
        # Loop over + dispaly attributes
        for attr_name, attr_properties in attributes.items():
            attr_val = getattr(config_instance, attr_name)
            
            # If not set we still display the default value as defined in the schema
            if attr_val=='':
                attr_val = attr_properties['init-value']
                
            # Dispalyattribute
            else:
                self._data_table.add_row(attr_name, attr_val, attr_properties['type'], attr_properties['multivalue'])
                
    @property
    def data_table(self)->DataTable:
        return self._data_table
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Edit cell when a row is selected"""
        self.app.push_screen(EditCellScreen(event))

