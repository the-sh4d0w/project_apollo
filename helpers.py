"""Some helpful things not necessarily directly associated with apollo directly.
Also contains code that would otherwise be redundant.
"""

import datetime
import logging

import rich.color
import rich.highlighter
import rich.logging
import rich.segment
import rich.style
import rich.theme
import textual.app
import textual.geometry
import textual.scroll_view
import textual.strip
import textual.widget
import textual.widgets

THEME = rich.theme.Theme({
    "log.datetime": rich.color.Color.from_rgb(44, 88, 172).name,
    "log.func_notset": rich.color.Color.from_rgb(128, 128, 128).name,
    "log.func_debug": rich.color.Color.from_rgb(0, 0, 255).name,
    "log.func_info": rich.color.Color.from_rgb(0, 255, 0).name,
    "log.func_warn": rich.color.Color.from_rgb(255, 255, 0).name,
    "log.func_error": rich.color.Color.from_rgb(255, 165, 0).name,
    "log.func_critical": rich.color.Color.from_rgb(255, 0, 0).name,
    "log.proc": rich.color.Color.from_rgb(25, 140, 162).name
})
FORMATTER = logging.Formatter(fmt="[{time}] [{func}/{levelname}] ({proc}) {message}",
                              datefmt="%Y-%m-%d %H:%M:%S", style="{")


class LogHighlighter(rich.highlighter.RegexHighlighter):
    """Apply style to logs."""

    base_style = "log."
    highlights = [
        r"(?P<datetime>(\[-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-"
        r"(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])Z\])",
        r"(?P<func_notset>\[[a-zA-Z_]*\/NOTSET\])",
        r"(?P<func_debug>\[[a-zA-Z_]*\/DEBUG\])",
        r"(?P<func_info>\[[a-zA-Z_]*\/INFO\])",
        r"(?P<func_warn>\[[a-zA-Z_]*\/WARNING\])",
        r"(?P<func_error>\[[a-zA-Z_]*\/ERROR\])",
        r"(?P<func_critical>\[[a-zA-Z_]*\/CRITICAL\])",
        r"(?P<proc>\([a-zA-Z0-9\- ]*\))"
    ]


class Logger:
    """Custom logger that logs to a file and the console
    with specific formatting and highlighting."""

    def __init__(self, name: str, file: str | None = None) -> None:
        """Initialize the logger.

        Arguments:
            - file: """
        self.name = name
        self.file = file
        self.log_console = rich.console.Console(theme=THEME)
        self.logger = logging.getLogger(name)

        # file handler setup
        date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_handler = logging.FileHandler(filename=f"logs/{self.name}-{date}.log",
                                           mode="w", encoding="utf-8")
        file_handler.setFormatter(FORMATTER)
        file_handler.setLevel(logging.DEBUG)

        # console handler setup
        console_handler = rich.logging.RichHandler(console=self.log_console, show_time=False,
                                                   show_level=False, show_path=False,
                                                   highlighter=LogHighlighter())
        console_handler.setFormatter(FORMATTER)
        console_handler.setLevel(logging.INFO)

        # general logging setup
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def add_handler(self, handler: logging.Handler) -> None:
        """Add another handler to logger. Literally just passed the argument
        to the addHandler method of the logger.

        Argument:
            - handler: handler to add.

        Returns:
            Nothing.
        """
        self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        """Just returns the logger.

        Returns:
            The logger (Obviously).
        """
        return self.logger


class Log(textual.scroll_view.ScrollView):
    """Render the log lines."""

    def __init__(self, path: str) -> None:
        """Initialize the log thing."""
        super().__init__()
        console = rich.console.Console(highlighter=LogHighlighter(),
                                       theme=THEME)
        with open(path, "r", encoding="utf-8") as file:
            log_text = file.readlines()
        # log_text = list(map(str, range(100)))
        self.virtual_size = textual.geometry.Size(max(len(line) for line in log_text),
                                                  len(log_text))
        self.log_lines = [textual.strip.Strip(list(console.render(
            text.replace("[", r"\[").replace("\n", ""))), len(text))
            for text in log_text]

    def render_line(self, y: int) -> textual.strip.Strip:
        """Render a line."""
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y
        if y >= len(self.log_lines):
            return textual.strip.Strip.blank(self.size.width)
        return self.log_lines[y].crop_extend(scroll_x, scroll_x + self.size.width, None)


class LogViewer(textual.app.App):
    """Log viewer ui."""

    def __init__(self, path: str) -> None:
        """Initializes the log viewer."""
        super().__init__()
        self.path = path
        self.console = rich.console.Console(highlighter=LogHighlighter(),
                                            theme=THEME)

    def on_ready(self) -> None:
        "Add text when DOM is ready."
        log = self.query_one("#log", textual.widgets.RichLog)
        log.highlighter = LogHighlighter()  # type: ignore
        with open(self.path, "r", encoding="utf-8") as file:
            log_text = file.readlines()
        for text in log_text:
            log.write(text.replace("\n", ""))

    def compose(self) -> textual.app.ComposeResult:
        """Composes the ui."""
        yield textual.widgets.Header(show_clock=True)
        yield textual.widgets.RichLog(id="log", highlight=True)
        yield textual.widgets.Footer()


# TODO(LogViewer):
# - create ascii art
# - select file
# - console argument (optional)


# TODO(Logger):
# - add functionality
# - make it easily usable

# TODO(bugfix):
# - only year as date breaks

if __name__ == "__main__":
    LogViewer("logs/comics-2023-09-21_18-40-32.log").run()
