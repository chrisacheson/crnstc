import time

from crnstc import definitions as defs
from crnstc import engine
from crnstc import ui


def main():
    game_engine = engine.GameEngine()
    user_interface = ui.UserInterface(game_engine)
    min_frame_time = 0

    if defs.FPS_CAP:
        min_frame_time = 1 / defs.FPS_CAP
        last_time = time.time()

    while True:
        if user_interface.quit_requested:
            user_interface.quit()
            break

        user_interface.render()

        if min_frame_time:
            this_time = time.time()
            frame_time = this_time - last_time
            delay = min_frame_time - frame_time
            last_time = this_time

            if delay > 0:
                time.sleep(delay)
