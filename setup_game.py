from __future__ import annotations

import copy
import lzma
import pickle
import traceback
from typing import Optional

import tcod

import color
from engine import Engine
import entity_factories
from game_map import GameWorld
from input_handlers import BaseEventHandler, MainGameEventHandler, PopupMessage


background_image = tcod.image.load("beeple_mike_winkelman_dvde.png")[:, :, :3]


def new_game() -> Engine:
    map_width = 80
    map_height = 43
    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    player = copy.deepcopy(entity_factories.player)
    engine = Engine(player=player)
    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
    )
    engine.game_world.generate_floor()
    engine.update_fov()
    engine.message_log.add_message("You've broken into a corporate facility"
                                   " that looks suspiciously like a roguelike"
                                   " dungeon.", color.welcome_text)
    return engine


def load_game(filename: str) -> Engine:
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))

    assert isinstance(engine, Engine)
    return engine


class MainMenu(BaseEventHandler):
    def on_render(self, console: tcod.Console) -> None:
        console.draw_semigraphics(background_image, 0, 0)
        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "Cyberpunk Roguelike (Name Subject to Change)",
            fg=color.menu_title,
            alignment=tcod.CENTER,
        )
        menu_width = 24

        for i, text in enumerate(["[N] Play a new game",
                                  "[C] Continue last game",
                                  "[Q] Quit"]):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=color.menu_text,
                bg=color.black,
                alignment=tcod.CENTER,
                bg_blend=tcod.BKGND_ALPHA(64),
            )

    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        if event.sym in (tcod.event.K_q, tcod.event.K_ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.K_c:
            try:
                return MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                return PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()
                return PopupMessage(self, f"Failed to load save:\n{exc}")
        elif event.sym == tcod.event.K_n:
            return MainGameEventHandler(new_game())

        return None
