#!/usr/bin/env python3

"""
Simple text box to display the properties of attributes in tree
"""

import conffwk
import confmodel

from texitual import on, log
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Input, Pretty, Label, Log, DataTable
from textual.reactive import reactive


class AttributeDisplay(Static):



    def compose(self)->ComposeResult:
        yield DataTable(id="main_table")
