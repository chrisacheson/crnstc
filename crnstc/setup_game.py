from __future__ import annotations

import copy
import lzma
import pickle
import traceback
from typing import Optional

import tcod

from crnstc import color
from crnstc.engine import Engine
from crnstc import entity_factories
from crnstc.game_map import GameWorld
from crnstc.input_handlers import (BaseEventHandler, MainGameEventHandler,
                                   PopupMessage)
from crnstc.geometry import Rectangle


background_image_path = "assets/beeple_mike_winkelman_dvde.png"
background_image = tcod.image.load(background_image_path)[:, :, :3]


def new_game() -> Engine:
    map_shape = Rectangle(x=0, y=0, w=80, h=43)
    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    player = copy.deepcopy(entity_factories.player)
    engine = Engine(player=player)
    engine.game_world = GameWorld(
        engine=engine,
        map_shape=map_shape,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
    )
    engine.game_world.generate_floor()
    engine.update_fov()
    engine.message_log.add_message("You've broken into a corporate facility"
                                   " that looks suspiciously like a roguelike"
                                   " dungeon.", color.welcome_text)
    combat_knife = copy.deepcopy(entity_factories.combat_knife)
    combat_knife.parent = player.inventory
    player.inventory.items.append(combat_knife)
    player.equipment.toggle_equip(combat_knife, add_message=False)
    kevlar_vest = copy.deepcopy(entity_factories.kevlar_vest)
    kevlar_vest.parent = player.inventory
    player.inventory.items.append(kevlar_vest)
    player.equipment.toggle_equip(kevlar_vest, add_message=False)
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
