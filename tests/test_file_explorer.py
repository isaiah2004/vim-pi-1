from src.main import VimPi, TextViewer
import os


# TEST SCREEN SWITCHING
async def test_editor_screen_switching():
    path = os.getcwd()
    app = VimPi(path)

    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        await pilot._wait_for_screen(0.30)
        # (app.screen_stack)
        assert app.screen.name == "FileExplorer"

        await pilot.press("ctrl+f")
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        assert app.screen.name == "FileExplorer"


# test editor screen layout
async def test_layout():
    app = VimPi()

    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        assert app.screen.name == "FileExplorer"

        assert app.query_one("#FileExplorerPanel") is not None

        assert app.query_one("#editor") is not None
        childrenNodes = app.query_one("#FileExplorerPanel").query_children()
        assert childrenNodes is not None


# test file loading
async def test_file_loading():
    app = VimPi()
    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        assert app.screen.name == "FileExplorer"

        fileContent = "This is a text file that is built solely for testing"
        with open("test.txt", "w") as f:
            f.write(fileContent)
            f.close()

        await pilot.press("tab")
        StepsToTestFile = os.listdir(os.getcwd()).index("test.txt") + 2

        for i in range(StepsToTestFile):
            await pilot.press("down")
        await pilot.press("enter")

        LoadedText = app.query_one(TextViewer).text
        assert "This is a text file that is built solely for testing" in LoadedText


# test file saving
async def test_file_saving():
    app = VimPi()
    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        assert app.screen.name == "FileExplorer"

        fileContentBeforeEdit = "This is a text file that is built solely for testing\nthe capabilities of file loading\n"
        with open("test.txt", "w") as f:
            f.write(fileContentBeforeEdit)
            f.close()

        t = [
            i
            for i in os.listdir(os.getcwd())
            if os.path.isdir(os.path.join(os.getcwd(), i))
        ] + [
            i
            for i in os.listdir(os.getcwd())
            if not os.path.isdir(os.path.join(os.getcwd(), i))
        ]
        StepsToTestFile = t.index("test.txt") + 1
        await pilot.press("tab")
        for i in range(StepsToTestFile):
            await pilot.press("down")
        await pilot.press("enter")

        await pilot.press("tab")
        for i in range(3):
            await pilot.press("down")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("ctrl+s")

        with open("test.txt", "r") as f:
            assert "hello" in "".join(f.readlines())
