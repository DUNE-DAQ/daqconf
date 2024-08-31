#!/usr/bin/env python3

import conffwk
import confmodel

import os.path

from textual import on, log
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Input, Pretty, Label, Log, DataTable
from textual.reactive import reactive

from search_bar import FileSearchBar, UidSearchBar, ClassSearchBar
"""
Python class containing configuration tree object
"""

class ConfigTree(Static):
    """
    Class for making a collapsable config tree
    """

        ##############
    # HACK: Hardcoding in variables for test example
    class_uid=reactive("")#"test-session"
    root_class_type=reactive("")#"Session"
    input_file="/afs/cern.ch/work/h/hwallace/private/software/dune-software/daq/runs/test_case_2/test-session.data.xml"

    input_config = reactive(conffwk.Configuration(f"oksconflibs:{input_file}"))      #conffwk.Configuration(f"oksconflibs:{input_file}")
    dal_input_config = reactive(None) #input_config.get_dal(root_class_type, class_uid) #input_config.get_dal(root_class_type, class_uid)
    ###########
    tree = None

    COLS = reactive([("Attribute", "Value"), ("", "")])

    def compose(self) -> ComposeResult:
        """
        Composes textual tree for schema file

        :return: ComposeResult
        """
        yield Label("Class Name")
        yield Input(id="class_search")
        yield Label("Class UID")
        yield Input(id="uid_search")
        self.tree = self.make_tree()
        yield self.tree
        yield DataTable(id="main_table")

    def make_tree(self)->Tree:
        tree: tree[dict] = Tree(f"[green]{self.input_file}[/green]", id="main_tree")
        tree.root.expand()
        return tree

    def get_branch_info(self, dal_object, input_tree_node)->None:
        """
        Recurssive method to find all attributes of a tree
        :input_tree: initial tree, should be the root branch

        :returns
        """

        if self.class_uid=="" or self.root_class_type=="" or self.input_file=="":
            return

        # attributes = self.input_config.attributes(dal_object.className(), True)

        # for a in attributes:
        #     if getattr(dal_object, a) == '':
        #         attr_str="[red]Not Set[/red]"
        #     else:
        #         attr_str = f"[blue]{getattr(dal_object, a)}[/blue]"
        #     input_tree_node.add_leaf(f"{a} = {attr_str}")


        relations = self.input_config.relations(dal_object.className(), True)
        for rel, rinfo in relations.items():
            rel_val = getattr(dal_object, rel)
            if not isinstance(rel_val,list):
                rel_val = [rel_val]
            for v in rel_val:
                if v is None:
                    continue

                # HW : Ugly
                if len(self.input_config.relations(v.className(), True)) == 0:
                    input_tree_node.add_leaf(f"[green]{getattr(v,'id')}[/green]@[yellow]{rinfo['type']}[/yellow]", data=v)
                else:
                    new_node  = input_tree_node.add(f"[green]{getattr(v,'id')}[/green]@[yellow]{rinfo['type']}[/yellow]", data=v, expand=False)
                    self.get_branch_info(v, new_node)





    def on_input_submitted(self, event: Input.Submitted):
        input_id = event.input.id
        input_value = event.input.value

        if input_id == "uid_search":
            self.class_uid=input_value
        elif input_id == "class_search":
            self.root_class_type = input_value

        if self.class_uid!="" and self.root_class_type!="":
            self.refresh_ui()

    def refresh_ui(self):
        self.dal_input_config =  self.input_config.get_dal(self.root_class_type, self.class_uid)

        new_node = self.tree.root.add(f"[green]{self.class_uid}[/green]@[yellow]{self.root_class_type}[/yellow]", data=self.dal_input_config)

        self.get_branch_info(self.dal_input_config, new_node)
        self.tree.refresh()


    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(*self.COLS[0])
        table.add_rows(self.COLS[1:])

        table.fixed_rows = 1
        table.zebra_stripes = True

    def on_tree_node_selected(self, event):
        node_value = event.node.data

        table = self.query_one(DataTable)

        table.clear()


        attributes = self.input_config.attributes(node_value.className(), True)

        if len(attributes) == 0:
            table.add_row('', '')
            return

        for a in attributes:

            attr = getattr(node_value, a)
            if attr == '':
                table.add_row(a, '')
            else:
                table.add_row(a, attr)
