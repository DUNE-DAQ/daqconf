#!/usr/bin/env python3

import conffwk
import confmodel

import os.path

from textual import on, log
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Input, Pretty, Label, Button
from textual.reactive import reactive

"""
Python class containing configuration tree object
"""

class ConfigTree(Static):
    """
    Class for making a collapsable config tree
    """

        ##############
    # HACK: Hardcoding in variables for test example
    _input_config = reactive(None)#reactive(conffwk.Configuration(f"oksconflibs:{input_file}"))      #conffwk.Configuration(f"oksconflibs:{input_file}")
    _dal_input_config = reactive(None) #input_config.get_dal(root_class_type, class_uid) #input_config.get_dal(root_class_type, class_uid)
    ###########
    tree = None


    CSS_PATH="textual_css/style_sheet.tcss"

    def compose(self) -> ComposeResult:
        """
        Composes textual tree for schema file

        :return: ComposeResult
        """
        self.tree = self.make_tree()
        yield self.tree

    def make_tree(self)->Tree:
        tree: tree[dict] = Tree(f"[red]Open Files[/red]", id="main_tree", data=None)
        tree.root.expand()
        return tree

    def get_branch_info(self, dal_object, input_tree_node)->None:
        """
        Recurssive method to find all attributes of a tree
        :input_tree: initial tree, should be the root branch

        :returns
        """
        if self._input_config is None or self._dal_input_config is None:
            log = self.query_one("RichLog")
            log.write("Error, couldn't find input configs")
            return

        relations = self._input_config.relations(dal_object.className(), True)
        for rel, rinfo in relations.items():
            rel_val = getattr(dal_object, rel)
            if not isinstance(rel_val,list):
                rel_val = [rel_val]
            for v in rel_val:
                if v is None:
                    continue

                # HW : Ugly
                if len(self._input_config.relations(v.className(), True)) == 0:
                    input_tree_node.add_leaf(f"[green]{getattr(v,'id')}[/green]@[yellow]{rinfo['type']}[/yellow]", data=v)
                else:
                    new_node  = input_tree_node.add(f"[green]{getattr(v,'id')}[/green]@[yellow]{rinfo['type']}[/yellow]", data=v, expand=False)
                    self.get_branch_info(v, new_node)

    def refresh_ui(self, input_config, dal_input_config):

        self._input_config = input_config
        self._dal_input_config = dal_input_config

        self.tree.data = self._input_config

        new_node = self.tree.root.add(f"[green]{getattr(self._dal_input_config, 'id')}[/green]@[yellow]{type(self._dal_input_config)}[/yellow]", data=self._dal_input_config)


        self.get_branch_info(self._dal_input_config, new_node)
        self.tree.refresh()


