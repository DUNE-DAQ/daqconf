from typing import Any
import numpy as np

from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode
from daqconf.textual_dbe.widgets.configuration_controller import ConfigurationController

class SelectionMenu(Static):
    '''
    Basic selection menu, builds tree from selection objects
    '''
    _tree = None
    
    def compose(self):        
        self._build_tree()
        yield self._tree
    
    def _build_tree(self):
        """Iteratively builds tree via dictionary. This should be generated in SelectionInterface"""

        # Grab current tree + config controller
        if self._tree is not None:
            self._tree.clear()
    
        self._tree = Tree(f"File Browser:")
        main_screen = self.app.get_screen("main")
        self._controller = main_screen.query_one("ConfigurationController")

        # Loop over interfaces + make sure they're up to date with config
        for key, interface in self._controller.get_interface().items():
            interface.recompose()

        # Check if the current interface is in the controller
        if self.id not in self._controller.get_interface().keys():
            raise ValueError(f"Cannot find {self._interface_label} in controller. \n  \
                             available interfaces are {self._controller.get_interface()}")

        # Grab root of tree        
        tree_root = self._tree.root
        tree_root.expand()
        
        # Sort out the tree nodes to be alphabetical + loop overtop level noes  
        for key, branch in sorted(self._controller.get_interface()[self.id].relationships.items()):
            tree_node = tree_root.add(f"[green]{key}[/green]", expand=False)            
            self.__build_tree_node(tree_node, branch, is_disabled=False, disabled_elements=[])
            

    def __build_tree_node(self, input_node: TreeNode, input_list: list, is_disabled: bool=False, disabled_elements: list=[]):
        """Recursively build tree nodes from a list of dictionaries"""
        
        # Check if we need to remove the node since it's empty
        if len(input_list)==0:
            input_node.remove()

        # Loop over the input list
        for config_item in input_list:
            # Check if it has sub-levels
            if isinstance(config_item, dict):
                # Print the DAL name
                config_key = list(config_item.keys())[0]
                if config_key.className() == "Session":
                    disabled_elements = config_key.disabled
                
                
                # Check if the item is disabled
                item_disabled = self.__check_item_disabled(config_key, disabled_elements) or is_disabled
                
                dal_str = self._controller.generate_rich_string(list(config_item.keys())[0], item_disabled)
                tree_node = input_node.add(dal_str, config_key)

                # Bit confusing, set ensure we're not multiply defining things in the tree,
                # for example disabled items in a session may also be defined elsewhere
                unique_config_objects = self.__get_unique_config_items(list(config_item.values())[0])
                
                self.__build_tree_node(tree_node, unique_config_objects, item_disabled, disabled_elements)
            else:
                # No sub-levels, just add the leaf
                item_disabled = self.__check_item_disabled(config_item, disabled_elements) or is_disabled
                input_node.add_leaf(self._controller.generate_rich_string(config_item, item_disabled), data=config_item)

    def on_tree_node_selected(self, event):
        # Selector
        controller:ConfigurationController = self.app.query_one("ConfigurationController")
        
        if event.node.data is not None: 
            controller.current_dal = event.node.data


    def __get_unique_config_items(self, input_list: list):
        """Get unique config items from a list of dictionaries
        
            this is very messy but it's the only way conffwk will play nice
        """

        # We can idenitify items by keys
        unique_items = np.zeros(len(input_list), dtype=bool)
        
        """ Okay this is a bit hacky
             Can't compare dicts directly to each other + schema
             so we compare the top level conf objects instead!
        """
        for i, item in enumerate(input_list):
            if isinstance(item, dict):
                if list(item.keys())[0] not in unique_items:
                    unique_items[i] = True
            elif item not in unique_items:
                unique_items[i] = True

        # Get all entries in input_list unique_items = True
        input_list = np.array(input_list)[unique_items]

        return input_list
    
    
    def __check_item_disabled(self, item, disabled_elements):
        """Check if an item is disabled"""
        return item in disabled_elements