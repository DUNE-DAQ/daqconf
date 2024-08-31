#!/usr/bin/env python

# DAQ imports
import conffwk
import confmodel

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static

from config_tree import ConfigTree


class ConffwkApp(App):
    """
    Main class containing conffwk app
    """
    def compose(self)->ComposeResult:
        yield Header()
        yield ConfigTree()
        yield Footer()

if __name__=="__main__":
    app =  ConffwkApp()
    app.run()
