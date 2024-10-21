from textual.screen import Screen
from textual.widgets import Footer
from textual.binding import Binding

# Textual OKS imports
from daqconf.textual_dbe.widgets.custom_rich_log import RichLogWError
from daqconf.textual_dbe.widgets.config_table import ConfigTable
from daqconf.textual_dbe.widgets.configuration_controller import ConfigurationController
from daqconf.textual_dbe.widgets.popups.file_io import SaveWithMessageScreen, OpenFileScreen
from daqconf.textual_dbe.widgets.popups.dropdown_selector import SelectSessionScreen
from daqconf.textual_dbe.app_structures.selection_panel import SelectionPanel
from daqconf.textual_dbe.widgets.popups.quit_screen import QuitScreen
from os import environ, path


class MainScreen(Screen):
    """Main screen for navigating python DBE
    """
    
    # Key binds
    BINDINGS = [
                Binding("ctrl+s", "save_configuration", "Save Configuration"),
                Binding("S", "save_configuration_with_message", "Save Configuration with Message"),
                Binding("o", "open_configuration", "Open Configuration"),
                # Binding("a", "add_configuration", "Add Configuration"),
                # Binding("del", "destroy_configuration", "Destroy Configuration"),
                Binding("ctrl+d", "toggle_disable", "Toggle Disable"),
                Binding("q", "request_quit", "Quit"),]
    
    
    
    def compose(self):
        """Compose main app
        """        
        # Import for app control
        self._config_controller = ConfigurationController()
        yield self._config_controller
        yield Footer()
        
        logger = RichLogWError(id="main_log", highlight=True, markup=True)
        yield logger
        
        # Splash screen
        logger.write("[red]========================================================================")
        logger.write("    [bold yellow]Welcome to the Textual Database Editor![/bold yellow]")
        logger.write("    [green]This is a work in progress, please use with[/green] [bold red]caution![/bold red]")
        logger.write("[red]========================================================================\n\n")
        

    def update_with_new_input(self, input_file_name: str):
        '''
        Update main screen to have a new input file.
        '''
        self._config_controller.new_handler_from_str(input_file_name)

        # Add interfaces
        self._config_controller.add_interface("class-selection")
        self._config_controller.add_interface("relation-selection")

        # Mount the selection panel
        try:
            self.mount(SelectionPanel())
        except:
            raise Exception("Selection panel not found, something's gone wrong")

        # Mount config table
        try:
            config_table = self.query_one(ConfigTable)
            config_table.update_table(self._config_controller.current_dal)
        except:
            config_table = ConfigTable(id="main_table")
            self.mount(config_table)

        # Refresh the screen for safety
        self.refresh()
        
        # Get logger (defined at the start)
        logger = self.query_one("RichLogWError")
        
        # Get the current database name
        current_database_path = self._config_controller.configuration.databases[0]
        data_base_name = path.basename(current_database_path)
        
        # Print everything!
        logger.write(f"[bold green]Opened new configuration file: [/bold green][bold red]{data_base_name}[/bold red][bold green].\nConnected databases are:[/bold green]\n" \
                     + "".join([f"   - [red]{db}[/red] \n" for db in self._config_controller.configuration.get_includes()]))

            
    def on_configuration_controller_changed(self, event):
        """Updates table based on global state of the configuration controller
        """        
        config_table = self.query_one(ConfigTable)
        if config_table is not None:
            config_table.update_table(event.dal)
        
    def action_save_configuration(self)->None:
        """Save current configuration
        """        
        config = self.query_one(ConfigurationController)
        config.commit_configuration("Update configuration")

    def action_save_configuration_with_message(self)->None:
        """Save current configuration with an update message
        """        
        self.app.push_screen(SaveWithMessageScreen())
        
    async def action_open_configuration(self) -> None:
        """Activate open file splash screen
        """        
        # Push the OpenFileScreen and wait for it to be closed
        await self.app.push_screen(OpenFileScreen())

    async def action_toggle_disable(self)->None:
        """Toggle disable on the selected configuration object
        """        
        if self._config_controller.can_be_disabled():
            await self.app.push_screen(SelectSessionScreen())
        
        # except:
        self.query_one(RichLogWError).write_error("Could not toggle disable configuration object")

    async def action_request_quit(self)->None:
        """Quit TDBE
        """
        self.app.push_screen(QuitScreen())
        

    """
    Currently adding/destroying configuration objects is not well implemented and is disabled
    """
    # async def action_add_configuration(self)->None:
    #     """Dunder method for adding configuration object
        
    #         CURRENTLY THIS IS A DUMMY METHOD USE WITH CAUTION
        
    #     """        
    #     self.query_one(RichLogWError).write("[yellow]ADD CONFIGURATION METHOD CALLED THIS IS CURRENTLY NOT WELL IMPLEMENTED![/yellow]")
    #     try:
    #         self._config_controller.add_new_conf_obj("GeoId", "dummy")
    #         menu = self.query_one(SelectionPanel)
    #         menu.refresh(recompose=True)
            
    #     except:
    #         self.query_one(RichLogWError).write_error(f"Could not add configuration object")
    
    # async def action_destroy_configuration(self)->None:
    #     """Dunder method for destroying configuration object
        
    #     CURRENTLY THIS IS A DUMMY METHOD USE WITH CAUTION
    #     """        
    #     self.query_one(RichLogWError).write("[yellow]DESTROY CONFIGURATION METHOD CALLED THIS IS CURRENTLY NOT WELL IMPLEMENTED![/yellow]")

    #     try:
    #         self._config_controller.destroy_conf_obj("GeoId", "dummy")
    #         menu = self.query_one(SelectionPanel)
    #         menu.refresh(recompose=True)
    #     except:
    #         self.query_one(RichLogWError).write_error("Could not destroy configuration object")
  
