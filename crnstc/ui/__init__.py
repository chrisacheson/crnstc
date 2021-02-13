"""Module containing all user interface code."""
import tcod

from crnstc.geometry import Rectangle
from crnstc.ui.input import InputHandler
from crnstc.ui.pages import TitleScreen


class UserInterface:
    """
    Main user interface class. Instantiated first when the program is started.
    Instantiates the game engine and other relevant classes. Passes input from
    the user to the game engine, and conveys results from the engine back to
    the user.

    """
    def run(self) -> None:
        """Start the game."""
        width_pixels = 1280
        height_pixels = 800
        self.game_name = "Cyberpunk Roguelike (Name Subject to Change)"

        tileset = tcod.tileset.load_tilesheet(
            path="assets/16x16-sb-ascii.png",
            columns=16,
            rows=16,
            charmap=tcod.tileset.CHARMAP_CP437,
        )

        with tcod.context.new(
            width=width_pixels,
            height=height_pixels,
            tileset=tileset,
            title=self.game_name,
            renderer=tcod.context.RENDERER_OPENGL2,
        ) as context:
            console = context.new_console(order="F")
            self.input_handler = InputHandler()
            self.show_title_screen()

            while True:
                console_shape = Rectangle(0, 0, console.width, console.height)
                self.current_page.render(surface=console, area=console_shape)
                context.present(console, integer_scaling=True)

                for event in tcod.event.wait():
                    context.convert_event(event)

                    if event.type == "QUIT":
                        raise SystemExit
                    elif event.type == "WINDOWRESIZED":
                        console = context.new_console(order="F")
                    else:
                        self.input_handler.dispatch(event)

    def show_title_screen(self) -> None:
        """Switch to the title screen page."""
        self.current_page = TitleScreen(ui=self)
