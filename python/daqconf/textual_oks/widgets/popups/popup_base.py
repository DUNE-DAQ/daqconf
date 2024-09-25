from textual.screen import ModalScreen
from typing import Any

class PopupBase(ModalScreen):
    def __init__(self, event: Any, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:


        super().__init__(name=name, id=id, classes=classes)
        