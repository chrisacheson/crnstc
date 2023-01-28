"""
Full-console widget arrangements, such as the title screen and main gameplay
screen.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import tcod

import crnstc.color as color
from crnstc.geometry import StretchyArea, StretchyLength
from crnstc.ui.input import InputCallback
from crnstc.ui.layouts import HorizontalLayout, PaddingLayout, VerticalLayout
from crnstc.ui.widgets import (Choice, ChoiceBox, ColorBox, ImageBox, TextBox,
                               Widget)

if TYPE_CHECKING:
    from crnstc.ui import UserInterface


class Page(Widget):
    """Base class inherited by other page classes."""
    def __init__(self, ui: UserInterface, *args, **kwargs):
        """
        Args:
            ui: Reference to the main user interface object.

        """
        super().__init__(*args, **kwargs)
        self.ui = ui


class TitleScreen(Page):
    """
    The first page shown to the user on startup. Displays the game name, title
    screen "graphics", and a new game/load/quit menu.

    """
    def __init__(self, ui: UserInterface):
        image_width = 80
        image_height = 50
        choices = (
            Choice("n", "Play a new game",
                   InputCallback(self.cb_menu_new_game)),
            Choice("c", "Continue last game",
                   InputCallback(self.cb_menu_load_game)),
            Choice("q", "Quit", InputCallback(self.cb_menu_quit)),
        )
        choices_width = max(len(choice.text) for choice in choices) + 4
        self.menu = ChoiceBox(
            size=StretchyArea.fixed(choices_width + 2, len(choices)),
            choices=choices,
            text_color=color.menu_text,
            bg_color=color.black,
            bg_blend=tcod.BKGND_ALPHA(64),
        )
        ui.input_handler.register(self.menu)

        super().__init__(
            ui=ui,
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
                                    size=StretchyArea.fixed(len(ui.game_name),
                                                            1),
                                    text=ui.game_name,
                                    text_color=color.menu_title,
                                ),
                            ],
                        ),
                        Widget(
                            layout=PaddingLayout(top=StretchyLength.fixed(0)),
                            children=[self.menu],
                        ),
                    ],
                ),
            ],
        )

    def cb_menu_new_game(self, data: object) -> None:
        """Called when the "new game" option is selected."""
        self.ui.input_handler.unregister(self.menu)
        self.ui.show_main_gameplay_screen()

    def cb_menu_load_game(self, data: object) -> None:
        """Called when the "continue game" option is selected."""
        print("load game")

    def cb_menu_quit(self, data: object) -> None:
        """Called when the "quit" option is selected."""
        raise SystemExit


class MainGameplayScreen(Page):
    """
    Screen that will be shown when the user starts playing the game. Displays a
    view of the game world, along with various status information.

    """
    def __init__(self, ui: UserInterface):
        world_pane = ColorBox(size=StretchyArea(min_width=80,
                                                min_height=43))
        status_pane = ColorBox()
        log_pane = ColorBox(size=StretchyArea(width_expansion=2.0,
                                              height_expansion=1.0))
        info_section = Widget(children=[status_pane, log_pane],
                              layout=HorizontalLayout())
        super().__init__(ui=ui, children=[world_pane, info_section],
                         layout=VerticalLayout())
