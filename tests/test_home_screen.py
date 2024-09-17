from src.main import VimPi


async def test_screens():
    app = VimPi()
    async with app.run_test() as pilot:
        await pilot._wait_for_screen(0.30)
        assert app.screen.name == "Home"
        
        assert app.query_one("#home-screen") is not None
        
