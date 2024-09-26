import os
import threading
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.screen import Screen
from textual.message import Message

from textual import on
from textual import log

from textual.widgets import Header, Footer, Button
from textual.widgets import Static, DirectoryTree, TextArea

from textual.containers import Vertical, Horizontal, VerticalScroll, Container
import pyperclip

from utils.Utils import Drive

HomePageText = r"""
 _____ _                     _
|  |  |_|_____    ___    ___|_|
|  |  | |     |  |___|  | . | |
 \___/|_|_|_|_|         |  _|_|
                        |_|    
"""

main_path = Path(__file__).resolve()

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


class DriveSyncScreen(Screen):
    drive_status = reactive("inactive")
    sync_thread = None

    def __init__(self, name: str, drive):
        super().__init__(name=name)
        self.drive = drive

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="drive-sync-content"):
            yield Static(id="status-message")
            yield Button("Synchronize", id="sync-button", variant="primary")
            yield Button("Return to Main Menu", id="main-menu-button", variant="primary")

    def on_mount(self):
        self.update_status()

    def watch_drive_status(self, status: str):
        self.update_status()

    def update_status(self):
        status_widget = self.query_one("#status-message", Static)
        sync_button = self.query_one("#sync-button", Button)

        if self.drive_status == "inactive":
            status_widget.update("Drive Sync is inactive.")
            sync_button.disabled = False
        elif self.drive_status == "activating":
            status_widget.update("Activating Drive Sync...")
            sync_button.disabled = True
        else:  # active
            status_widget.update("Drive Sync is active.")
            sync_button.disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sync-button":
            self.action_enable_drive_sync()
        elif event.button.id == "main-menu-button":
            self.app.pop_screen()

    def action_enable_drive_sync(self):
        if self.drive_status == "inactive":
            self.drive_status = "activating"
            self.app.call_after_refresh(self.perform_sync)
        else:
            self.notify("Drive Sync is already active or activating.")

    def sync_thead(self):
        while True:
            time.sleep(60)
            self.drive.synchronize(self.app.CURRENT_DIR, self.drive.get_or_create_folder("vim_pi"))

    def perform_sync(self):
        self.drive = self.app.drive = Drive(credentials_path=main_path.parent)
        self.drive.synchronize(self.app.CURRENT_DIR, self.drive.get_or_create_folder("vim_pi"))
        self.sync_thread = threading.Thread(target=self.sync_loop)
        self.sync_thread.start()
        self.drive_status = "active"


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
    BINDINGS=[
        ("ctrl+s", "save_current_file()", "Save File"),
        ("ctrl+w", "close_current_file()", "Close file"),
        ("ctrl+insert", "copy_selected_text()", "Copy"),
        ("alt+insert", "paste_selected_text()", "Paste"),
    ]
    def action_copy_selected_text(self):
        textToCopy = self.selected_text
        pyperclip.copy(textToCopy)

    # default behavior is paste keep here for features like replace paste etc.
    def action_paste_selected_text(self):
        log("".join(['--']*30))
        sel=self.selection
        log(pyperclip.paste())
        self.replace(pyperclip.paste(),sel.start,sel.end)
        pass
    pass


class FileExplorerAndEditorScreen(Screen):
    BINDINGS = [
        ("ctrl+f", "toggle_file_explorer()", "Home Screen"),
        ("ctrl+s", "save_current_file()", "Save File"),
        ("ctrl+w", "close_current_file()", "Close file"),
    ]

    def __init__(self, name, CURRENT_DIR, isFileOpen: bool = False, drive = None):
        self.CURRENT_DIR = CURRENT_DIR
        self.isFileOpen = isFileOpen
        self.drive = drive
        super().__init__(name=name)

    # The composition of the Editing screen
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            with VerticalScroll(id="left-pane"):
                yield FileExplorer(path=self.CURRENT_DIR, id="FileExplorerPanel")
            with Container(id="right-pane"):
                TextViewerObject = TextViewer(id="editor", disabled=True).code_editor(
                    id="editor"
                )
                TextViewerObject.load_text("Open file to edit")
                TextViewerObject.disabled=True
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
                    self.isFileOpen = True
                    if self.drive:
                        self.drive.synchronize(self.app.CURRENT_DIR, self.drive.get_or_create_folder("vim_pi"))
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
            self.query_one("#editor", TextViewer).load_text("Open File to edit")
            self.query_one("#editor", TextViewer).disabled = True
        else:
            self.notify("file not open")
    pass


# App
class VimPi(App):
    CSS_PATH = "layout.tcss"
    # Add a binding for the screen switching
    BINDINGS = [
        ("ctrl+f", "toggle_file_explorer()", "File Explorer"),
        ("ctrl+g", "enable_drive_sync()", "Enable Drive"),
        ("ctrl+q", "quit_app()", "Quit"),
    ]

    def __init__(self, CURRENT_DIR=None):
        if CURRENT_DIR == None:
            self.CURRENT_DIR = os.getcwd()
        else:
            self.CURRENT_DIR = CURRENT_DIR
        super().__init__()
        self.drive = None

    def on_mount(self) -> None:
        # register home screen
        self.install_screen(Home(name="Home"), name="Home")
        self.install_screen(
            FileExplorerAndEditorScreen(
                name="FileExplorer", CURRENT_DIR=self.CURRENT_DIR, drive=self.drive
            ),
            name="FileExplorer",
        )
        self.install_screen(DriveSyncScreen(name="DriveSyncScreen", drive=self.drive), name="DriveSyncScreen")
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

    def action_enable_drive_sync(self):
        self.push_screen("DriveSyncScreen")

    @on(FileExplorer.TextViewerUpdated)
    def load_new_file(self, message: FileExplorer.TextViewerUpdated) -> None:
        self.query_one("#editor", TextViewer).load_text(message.lines)
        self.query_one(FileExplorerAndEditorScreen).isFileOpen=True
        self.query_one("#editor", TextViewer).disabled = False
        log("The editor has updated")

    def action_quit_app(self):
        self.app.exit()


# initialise
if __name__ == "__main__":
    VimPi().run()
