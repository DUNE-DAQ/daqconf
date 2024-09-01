#!/usr/bin/env python 3

'''
Object controller
'''

import conffwk
import confmodel

import os.path

from custom_search_bar import SearchBar
from config_table import ConfigTable
from config_tree import ConfigTree

from textual.widgets import Header, Footer, Tree, RichLog
from textual.app import App
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll

class MainScreen(Screen):
    """
    Controller object
    """

    def compose(self):
        yield SearchBar()
        yield ConfigTable()
        yield ConfigTree(id="config_tree")

        yield Header()
        yield Footer()

    def on_button_pressed(self, event):

        tree = self.query_one(ConfigTree)
        search = self.query_one(SearchBar)
        table = self.query_one(ConfigTable)

        if search.open_configs():
            tree.refresh_ui(*search.get_configs())
            table.update_config(search.get_configs()[0])



    def on_tree_node_selected(self, event):
        table = self.query_one(ConfigTable)
        table.update_table(event)


class AppController(App):
    SCREENS = {"main": MainScreen}

    CSS_PATH="textual_css/style_sheet.tcss"

    def on_mount(self):
        self.push_screen("main")
