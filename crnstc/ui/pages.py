"""
Full-console widget arrangements, such as the title screen and main gameplay
screen.

"""
import tcod

import crnstc.color as color
from crnstc.geometry import StretchyArea, StretchyLength
from crnstc.ui.layouts import PaddingLayout, VerticalLayout
from crnstc.ui.widgets import ImageBox, TextBox, Widget


class Page(Widget):
    """Base class inherited by other page classes."""
    pass


class TitleScreen(Page):
    """
    The first page shown to the user on startup. Displays the game name, title
    screen "graphics", and a new game/load/quit menu.

    """
    def __init__(self, game_name: str):
        """
        Args:
            game_name: What are we playing?

        """
        image_width = 80
        image_height = 50
        choices = ["[N] Play a new game",
                   "[C] Continue last game",
                   "[Q] Quit"]
        choices_width = max(len(choice) for choice in choices)

        super().__init__(
            layout=PaddingLayout(),
            children=[
                ImageBox(
                    filename="assets/beeple_mike_winkelman_dvde.png",
                    size=StretchyArea.fixed(image_width, image_height),
                    layout=VerticalLayout(),
                    children=[
                        Widget(
                            layout=PaddingLayout(
                                top=StretchyLength.fixed(
                                    image_height // 2 - 4
                                ),
                                bottom=StretchyLength.fixed(1),
                            ),
                            children=[
                                TextBox(
                                    size=StretchyArea.fixed(len(game_name), 1),
                                    text=game_name,
                                    text_color=color.menu_title,
                                ),
                            ],
                        ),
                        Widget(
                            layout=PaddingLayout(top=StretchyLength.fixed(0)),
                            children=[
                                TextBox(
                                    size=StretchyArea.fixed(choices_width + 2,
                                                            len(choices)),
                                    text="\n".join(choices),
                                    text_color=color.menu_text,
                                    bg_color=color.black,
                                    bg_blend=tcod.BKGND_ALPHA(64),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
