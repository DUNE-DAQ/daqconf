from pathlib import Path
from typing import Iterable

from textual.screen import ModalScreen
from textual.widgets import DirectoryTree

class DatabaseDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path])->Iterable[Path]:
        return [path for  path in paths if not path.name.endswith(".data.xml")]
    
class DirectoryTreeScreen(ModalScreen):
    def compose(self):
        yield DatabaseDirectoryTree("./")