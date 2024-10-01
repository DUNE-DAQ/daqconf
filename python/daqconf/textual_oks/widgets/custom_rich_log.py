from textual.widgets import Static, RichLog
from rich.logging import RichHandler
from rich.console import ConsoleRenderable, RichCast

# Extends rich error log to have errors prints [will make prettier as time goes on!]

class RichLogWError(RichLog):
    def write_error(self, exception: Exception):
        super().write(f"ERROR: [red]{str(exception)}")
    