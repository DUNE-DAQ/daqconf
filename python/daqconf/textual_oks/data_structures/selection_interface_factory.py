from textual_oks.data_structures.configuration_handler import ConfigurationHandler

class SelectionInterfaceFactory:
    @classmethod
    def get_interface(cls, interface_name: str, configuration):
        match(interface_name):
            case "class-selection":
                from textual_oks.data_structures.selection_interface import ClassSelectionMenu
                return ClassSelectionMenu(configuration)

            case "relation-selection":
                from textual_oks.data_structures.selection_interface import RelationalSelectionMenu
                return RelationalSelectionMenu(configuration)
            
            case _:
                raise Exception(f"Cannot find {interface_name}")
