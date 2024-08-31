#!/usr/bin/env python3
"""
Generic Search bar object.
"""
from textual.widgets import Input, Pretty, Static, Label
from textual.app import ComposeResult
from textual.validation import Function, Number, ValidationResult, Validator
from textual import on

import os

class FileSearchBar(Static):
    def compose(self)->ComposeResult:
        yield Label("Press Enter to search for a file")
        yield Input(id="file_search", validators=[FileValidator()])
        yield Pretty([])

    @on(Input.Submitted)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        # Updating the UI to show the reasons why validation failed
        if not event.validation_result.is_valid:
            self.query_one(Pretty).update(event.validation_result.failure_descriptions)
        else:
            self.query_one(Pretty).update([])

class FileValidator(Validator):
    def validate(self, input_file: str):
        if not os.path.isfile(input_file):
            return self.failure(f"[red]ERROR:File not found[/red]")

        return self.success()


class UidSearchBar(Static):
    def compose(self)->ComposeResult:
        yield Label("Press Enter to search schema")
        yield Input(id="uid_search")
        yield Pretty([])

class ClassSearchBar(Static):
    def compose(self)->ComposeResult:
        yield Label("Press Enter to search class")
        yield Input(id="class_search")
        yield Pretty([])
