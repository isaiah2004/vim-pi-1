from src.main import VimPi, TextViewer
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

#test file loading
async def test_copy():
    app = VimPi()
    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"

        await pilot.press("ctrl+f")
        assert app.screen.name == "FileExplorer"

        await pilot.press("tab")
        StepsToTestFile = os.listdir(os.getcwd()).index('test.txt')+2

        for i in range(StepsToTestFile):
            await pilot.press("down")
        await pilot.press("enter")
        
        await pilot.press('tab')
        
        for i in range(3):
            await pilot.press('shift+down')
        await pilot.press('ctrl+insert')
        await pilot.press('right')
        await pilot.press('enter')
        await pilot.press('enter')
        await pilot.press('alt+insert')
        
        FinalText = app.query_one(TextViewer).text
        
        expectedText=r'''This is a text file that is built solely for testing
the capabilities of file loading
hello

This is a text file that is built solely for testing
the capabilities of file loading
hello'''

        assert FinalText == expectedText