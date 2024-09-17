import os
from pathlib import Path
from typing import Type

from textual.app import App, ComposeResult
from textual.driver import Driver
from textual.screen import Screen
from textual.message import Message

from textual import on
from textual import log

from textual.widgets import Header, Footer, Static
from textual.widgets import Static, DirectoryTree, TextArea

from textual.containers import Vertical, Horizontal, VerticalScroll, Container
import pyperclip

HomePageText = r"""
 _____ _                     _
|  |  |_|_____    ___    ___|_|
|  |  | |     |  |___|  | . | |
 \___/|_|_|_|_|         |  _|_|
                        |_|    
"""

# Home screen
class Home(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(HomePageText, id="home-screen")
        with Vertical(id="commands-box"):
            yield Static("Vim in Python \n")
            yield Static("ctrl+f - file Explorer")
            yield Static("ctrl+q - quit")


    pass


class FileExplorer(DirectoryTree):
    def __init__(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        SelectedFile=None
    ) -> None:
        self.SelectedFile = SelectedFile
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)

    class TextViewerUpdated(Message):
        def __init__(self, lines: str, SelectedFile=None) -> None:
            self.lines = lines
            super().__init__()

    @on(DirectoryTree.FileSelected)
    def file_selected(self, message: DirectoryTree.FileSelected) -> None:
        # Access the properties of the message and perform actions accordingly
        file_path = message.path
        self.SelectedFile = file_path
        # ... do something with the file_path
        text = open(file_path).readlines()
        FILE_TEXT = "".join(text)
        # log(text)
        log("-----------------------------------------------------------")
        log(FILE_TEXT)
        log("-----------------------------------------------------------")
        self.post_message(self.TextViewerUpdated(FILE_TEXT))


class TextViewer(TextArea):
    
    pass


class FileExplorerAndEditorScreen(Screen):
    BINDINGS = [
        ("ctrl+f", "toggle_file_explorer()", "Home Screen"),
        ("ctrl+s", "save_current_file()", "Save File"),
        ("ctrl+w", "close_current_file()", "Close file")
    ]
    def __init__(self, name, CURRENT_DIR,isFileOpen : bool=False):
        self.CURRENT_DIR = CURRENT_DIR
        self.isFileOpen=isFileOpen
        super().__init__(name=name)

    # The composition of the Editing screen
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            with VerticalScroll(id="left-pane"):
                yield FileExplorer(path=self.CURRENT_DIR,id='FileExplorerPanel')
            with Container(id="right-pane"):
                TextViewerObject = TextViewer(id="editor", disabled=True).code_editor(id="editor")
                TextViewerObject.load_text("Open file to edit")
                yield TextViewerObject

    def action_save_current_file(self):
        try:
            file_path = self.query_one(FileExplorer).SelectedFile
            if file_path:
                data = self.query_one("#editor", TextViewer).text
                if os.path.isfile(file_path):
                    # File exists, write data to the file
                    with open(file_path, "w") as f:
                        f.write(data)
                    self.isFileOpen=True
                    self.notify("File Saved Successfully.")
                else:
                    self.notify("File does not exist. At least, not anymore.")
            else:
                self.notify("No file selected.")
        except Exception as e:
            log(e)
            self.notify("e")

    def action_close_current_file(self):
        if self.isFileOpen:
            self.query_one('#editor',TextViewer).load_text("Open File to edit")
            self.query_one("#editor", TextViewer).disabled = True
        else:
            self.notify('file not open')
    pass



# App
class VimPi(App):
    CSS_PATH = "layout.tcss"
    # Add a binding for the screen switching
    BINDINGS = [
        ("ctrl+f", "toggle_file_explorer()", "File Explorer"),
        ("ctrl+q", "quit_app()","Quit")
    ]
    def __init__(self, CURRENT_DIR=None):
        if(CURRENT_DIR==None):
            self.CURRENT_DIR=os.getcwd()
        else:
            self.CURRENT_DIR=CURRENT_DIR
        super().__init__()

    def on_mount(self) -> None:
        # register home screen
        self.install_screen(Home(name="Home"), name="Home")
        self.install_screen(
            FileExplorerAndEditorScreen(name="FileExplorer", CURRENT_DIR=self.CURRENT_DIR),
            name="FileExplorer"
        )
        # push home screen
        self.push_screen("Home")

    def action_toggle_file_explorer(self):
        log("Screen toggled")
        log(str(Home()._get_virtual_dom()))
        if self.screen_stack[-1].name == "Home":
            log("True")
            self.push_screen("FileExplorer")
        else:
            log("Revert to Home")
            self.pop_screen()

    @on(FileExplorer.TextViewerUpdated)
    def LoadNewFile(self, message: FileExplorer.TextViewerUpdated) -> None:
        self.query_one("#editor", TextViewer).load_text(message.lines)
        self.query_one("#editor", TextViewer).disabled = False
        log("The editor has updated")

    def action_quit_app(self):
        self.app.exit()

# initialise
if __name__ == "__main__":
    VimPi().run()
