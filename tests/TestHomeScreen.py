import pytest
from textual.app import App
from textual.widgets import Static
from textual.containers import Vertical
from textual.screen import Screen
from main import Home

@pytest.fixture
def home_screen():
    return Home()

def test_home_screen_contains_header(home_screen):
    header = home_screen.query_one("Header")
    assert header is not None

def test_home_screen_contains_footer(home_screen):
    footer = home_screen.query_one("Footer")
    assert footer is not None

def test_home_screen_contains_home_text(home_screen):
    home_text = home_screen.query_one("#Home-screen", Static)
    assert home_text is not None
    assert "Vim in Python" in home_text.renderable

def test_home_screen_contains_commands_box(home_screen):
    commands_box = home_screen.query_one("#commands-box", Vertical)
    assert commands_box is not None
