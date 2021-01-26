from __future__ import annotations

from typing import Callable, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

import tcod.event

import actions
from actions import Action, BumpAction, WaitAction, PickupAction
import color
import exceptions
from utils import clamp

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item


move_keys = {
    # Arrow keys
    tcod.event.K_UP: (0, -1),
    tcod.event.K_DOWN: (0, 1),
    tcod.event.K_LEFT: (-1, 0),
    tcod.event.K_RIGHT: (1, 0),
    tcod.event.K_HOME: (-1, -1),
    tcod.event.K_END: (-1, 1),
    tcod.event.K_PAGEUP: (1, -1),
    tcod.event.K_PAGEDOWN: (1, 1),
    # Numpad keys
    tcod.event.K_KP_1: (-1, 1),
    tcod.event.K_KP_2: (0, 1),
    tcod.event.K_KP_3: (1, 1),
    tcod.event.K_KP_4: (-1, 0),
    tcod.event.K_KP_6: (1, 0),
    tcod.event.K_KP_7: (-1, -1),
    tcod.event.K_KP_8: (0, -1),
    tcod.event.K_KP_9: (1, -1),
    # Vi keys
    tcod.event.K_h: (-1, 0),
    tcod.event.K_j: (0, 1),
    tcod.event.K_k: (0, -1),
    tcod.event.K_l: (1, 0),
    tcod.event.K_y: (-1, -1),
    tcod.event.K_u: (1, -1),
    tcod.event.K_b: (-1, 1),
    tcod.event.K_n: (1, 1),
}

wait_keys = {
    tcod.event.K_PERIOD,
    tcod.event.K_KP_5,
    tcod.event.K_CLEAR,
}

confirm_keys = {
    tcod.event.K_RETURN,
    tcod.event.K_KP_ENTER,
}


@dataclass
class EventHandler(tcod.event.EventDispatch[Action]):
    engine: Engine

    def handle_events(self, event: tcod.event.Event) -> None:
        self.handle_action(self.dispatch(event))

    def handle_action(self, action: Optional[Action]) -> bool:
        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False

        self.engine.handle_enemy_turns()
        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)


class AskUserEventHandler(EventHandler):
    def handle_action(self, action: Optional[Action]) -> bool:
        if super().handle_action(action):
            self.engine.event_handler = MainGameEventHandler(self.engine)
            return True

        return False

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        if event.sym in {
            tcod.event.K_LSHIFT,
            tcod.event.K_RSHIFT,
            tcod.event.K_LCTRL,
            tcod.event.K_RCTRL,
            tcod.event.K_LALT,
            tcod.event.K_RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
        self,
        event: tcod.event.MouseButtonDown,
    ) -> Optional[Action]:
        return self.on_exit()

    def on_exit(self) -> Optional[Action]:
        self.engine.event_handler = MainGameEventHandler(self.engine)
        return None


class InventoryEventHandler(AskUserEventHandler):
    title = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        num_inventory_items = len(self.engine.player.inventory.items)
        height = num_inventory_items + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0
        width = len(self.title) + 4
        console.draw_frame(x=x, y=y, width=width, height=height,
                           title=self.title, clear=True, fg=color.white,
                           bg=color.black)

        if num_inventory_items > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                console.print(x + 1, y + i + 1, f"({item_key}) {item.name}")
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.",
                                                    color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[Action]:
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    title = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[Action]:
        return item.consumable.get_action(self.engine.player)


class InventoryDropHandler(InventoryEventHandler):
    title = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[Action]:
        return actions.DropItem(self.engine.player, item)


@dataclass
class SelectIndexHandler(AskUserEventHandler):
    def __post_init__(self):
        player = self.engine.player
        self.engine.mouse_location = player.x, player.y

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.tiles_rgb["bg"][x, y] = color.white
        console.tiles_rgb["fg"][x, y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        key = event.sym

        if key in move_keys:
            modifier = 1

            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5

            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10

            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = move_keys[key]
            x += dx * modifier
            y += dy * modifier
            x = clamp(0, x, self.engine.game_map.width - 1)
            y = clamp(0, y, self.engine.game_map.height - 1)
            self.engine.mouse_location = x, y
            return None
        elif key in confirm_keys:
            return self.on_index_selected(*self.engine.mouse_location)

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self,
        event: tcod.event.MouseButtonDown,
    ) -> Optional[Action]:
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)

        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    def on_index_selected(self, x: int, y: int) -> None:
        self.engine.event_handler = MainGameEventHandler(self.engine)


@dataclass
class RangedAttackHandler(SelectIndexHandler):
    callback: Callable[[Tuple[int, int]], Optional[Action]]

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        # https://github.com/python/mypy/issues/5485
        return self.callback((x, y))  # type: ignore


@dataclass
class AreaRangedAttackHandler(RangedAttackHandler):
    radius: int

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.draw_frame(
            x=x - self.radius,
            y=y - self.radius,
            width=self.radius * 2 + 1,
            height=self.radius * 2 + 1,
            fg=color.red,
            clear=False,
        )


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None
        key = event.sym
        player = self.engine.player

        if key in move_keys:
            action = BumpAction(player, *move_keys[key])
        elif key in wait_keys:
            action = WaitAction(player)
        elif key == tcod.event.K_ESCAPE:
            raise SystemExit()
        elif key == tcod.event.K_v:
            self.engine.event_handler = HistoryViewer(self.engine)
        elif key == tcod.event.K_g:
            action = PickupAction(player)
        elif key == tcod.event.K_i:
            self.engine.event_handler = InventoryActivateHandler(self.engine)
        elif key == tcod.event.K_d:
            self.engine.event_handler = InventoryDropHandler(self.engine)
        elif key == tcod.event.K_SLASH:
            self.engine.event_handler = LookHandler(self.engine)

        return action


class GameOverEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            raise SystemExit()


cursor_y_keys = {
    tcod.event.K_UP: -1,
    tcod.event.K_DOWN: 1,
    tcod.event.K_PAGEUP: -10,
    tcod.event.K_PAGEDOWN: 10,
}


@dataclass
class HistoryViewer(EventHandler):
    def __post_init__(self):
        self.log_length = len(self.engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        log_console = tcod.Console(console.width - 6, console.height - 6)
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(0, 0, log_console.width, 1, "Message History",
                              alignment=tcod.CENTER)
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in cursor_y_keys:
            adjust = cursor_y_keys[event.sym]

            if adjust < 0 and self.cursor == 0:
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                self.cursor = 0
            else:
                self.cursor = clamp(0, self.cursor + adjust,
                                    self.log_length - 1)
        elif event.sym == tcod.event.K_HOME:
            self.cursor = 0
        elif event.sym == tcod.event.K_END:
            self.cursor = self.log_length - 1
        else:
            self.engine.event_handler = MainGameEventHandler(self.engine)
