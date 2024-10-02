from textual_dbe.data_structures.configuration_handler import ConfigurationHandler

class SelectionInterfaceFactory:
    @classmethod
    def get_interface(cls, interface_name: str, configuration: ConfigurationHandler):
        """Very simple factory for generating selection interfaces

        Arguments:
            interface_name -- Name of interface (either "class-selection" or "relation-selection")
            configuration -- ConfigurationHandler object

        Raises:
            Exception: If interface_name is not recognised

        Returns:
            SelectionInterface -- Either ClassSelectionMenu or RelationalSelectionMenu
        """
        match(interface_name):
            case "class-selection":
                from textual_dbe.data_structures.selection_interface import ClassSelectionMenu
                return ClassSelectionMenu(configuration)

            case "relation-selection":
                from textual_dbe.data_structures.selection_interface import RelationalSelectionMenu
                return RelationalSelectionMenu(configuration)
            
            case _:
                raise Exception(f"Cannot find {interface_name}")
