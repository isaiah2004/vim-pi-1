from textual.app import App, ComposeResult
from textual.screen import Screen

from textual.widgets import Header,Footer, Static

from textual.containers import  Vertical

HomePageText="""
 _____ _                     _
|  |  |_|_____    ___    ___|_|
|  |  | |     |  |___|  | . | |
 \___/|_|_|_|_|         |  _|_|
                        |_|
"""

#Home screen
class Home(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(HomePageText,id="Home-screen")
        with Vertical(id="commands-box"):
            yield Static("Vim in Python \n")
            yield Static("f - file Explorer")
            yield Static("q - quit")
    pass


# App
class VimPi(App):

    CSS_PATH ='layout.tcss'
    def on_mount(self) -> None:
        #register home screen
        self.install_screen(Home(name='Home'), name="Home")
        # push home screen
        self.push_screen('Home')

# initialise
if __name__=="__main__":
    VimPi().run()