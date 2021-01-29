#!/usr/bin/env python3
import traceback

import tcod

from crnstc import color
from crnstc import exceptions
from crnstc.input_handlers import BaseEventHandler, EventHandler
from crnstc import setup_game


def save_game(handler: BaseEventHandler, filename: str) -> None:
    if isinstance(handler, EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")


def main() -> None:
    screen_width = 80
    screen_height = 50

    tileset = tcod.tileset.load_tilesheet(path="assets/16x16-sb-ascii.png",
                                          columns=16, rows=16,
                                          charmap=tcod.tileset.CHARMAP_CP437)
    root_console = tcod.Console(width=screen_width, height=screen_height,
                                order="F")

    handler: BaseEventHandler = setup_game.MainMenu()

    with tcod.context.new(
        columns=root_console.width,
        rows=root_console.height,
        tileset=tileset,
        title="Cyberpunk Roguelike (Name Subject to Change)",
        renderer=tcod.context.RENDERER_OPENGL2,
    ) as context:
        try:
            while True:
                root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception:
                    traceback.print_exc()

                    if isinstance(handler, EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(),
                            color.error,
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:
            save_game(handler, "savegame.sav")
            raise
        except BaseException:
            save_game(handler, "savegame.sav")
            raise


if __name__ == "__main__":
    main()
