#!/usr/bin/env python3
import conffwk
import confmodel

import os.path

from textual import on, log
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Tree, Static, Input, Pretty, Label, Log, DataTable
from textual.reactive import reactive
from typing import Any

class ConfigTable(Static):


    COLS = reactive([("Attribute", "Value", "Type"), ("", "","")])
    _input_config = None
    _input_dal_config = None

    def compose(self):
        yield DataTable(id="main_table")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(*self.COLS[0])
        table.add_rows(self.COLS[1:])
        table.fixed_rows = 1
        table.zebra_stripes = True


    def update_table(self, event):

        self._input_dal_config = event.node.data

        if self._input_dal_config is None or self._input_config is None:
            return

        table = self.query_one(DataTable)

        table.clear()

        attributes = self._input_config.attributes(self._input_dal_config.className(), True)


        for a in attributes:

            attr = getattr(self._input_dal_config, a)
            if attr == '':
                table.add_row(a, "[red]Not Set[/red]")
            else:
                table.add_row(a, attr, type(a))

        relations = self._input_config.relations(self._input_dal_config.className(), True)
        for rel, rinfo in relations.items():
            rel_val = getattr(self._input_dal_config, rel)
            table.add_row(rel, rel_val, "Relationship")

        if len(relations)+len(attributes) ==0:
            table.add_row("","","")

    def update_config(self, new_config):
        self._input_config = new_config


    def update_oks_config(self, input_attr: str, input_value):
        try:
            setattr(self._input_dal_config, input_attr, input_value)
            self._input_config.update_dal(self._input_dal_config)
            self._input_config.commit(f"Changed {input_attr}")
        except:
            return


    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:

        cell_value: Any = event.value
        if event.coordinate.row==0 or event.coordinate.column!=1:
            return

        self.app.push_screen(EditCellScreen(cell_value))


class EditCellScreen(ModalScreen):
    def __init__(
        self,
        cell_value: Any,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.cell_value = cell_value


    def compose(self) -> ComposeResult:
        yield Input()

    def on_mount(self) -> None:
        cell_input = self.query_one(Input)
        cell_input.value = str(self.cell_value)

        cell_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        main_screen = self.app.get_screen("main")

        table = main_screen.query_one(DataTable)
        table.update_cell_at(
            table.cursor_coordinate,
            event.value,
            update_width=True,
        )

        config_table = main_screen.query_one(ConfigTable)
        config_table.update_oks_config(table.get_cell_at((table.cursor_coordinate.row, 0)), event.value)

        self.app.pop_screen()
