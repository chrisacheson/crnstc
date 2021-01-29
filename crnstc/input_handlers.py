from __future__ import annotations

import os
from typing import Callable, Tuple, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass

import tcod.event

from crnstc import actions
from crnstc.actions import Action, BumpAction, WaitAction, PickupAction
from crnstc import color
from crnstc import exceptions
from crnstc.utils import clamp

if TYPE_CHECKING:
    from crnstc.engine import Engine
    from crnstc.entity import Item


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


ActionOrHandler = Union[Action, "BaseEventHandler"]


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        state = self.dispatch(event)

        if isinstance(state, BaseEventHandler):
            return state

        assert not isinstance(state, Action), f"{self!r} can't handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()


@dataclass
class PopupMessage(BaseEventHandler):
    parent: BaseEventHandler
    text: str

    def on_render(self, console: tcod.Console) -> None:
        self.parent.on_render(console)
        console.tiles_rgb["fg"] //= 8
        console.tiles_rgb["bg"] //= 8
        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=tcod.CENTER,
        )

    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        return self.parent


@dataclass
class EventHandler(BaseEventHandler):
    engine: Engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        action_or_state = self.dispatch(event)

        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state

        if self.handle_action(action_or_state):
            if not self.engine.player.is_alive:
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)

            return MainGameEventHandler(self.engine)

        return self

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

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)


class AskUserEventHandler(EventHandler):
    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
    ) -> Optional[ActionOrHandler]:
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        return MainGameEventHandler(self.engine)


class CharacterScreenEventHandler(AskUserEventHandler):
    title = "Character Information"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0
        width = len(self.title) + 4
        console.draw_frame(x=x, y=y, width=width, height=7, title=self.title,
                           clear=True, fg=color.white, bg=color.black)
        level = self.engine.player.level
        fighter = self.engine.player.fighter
        console.print(x=x + 1, y=y + 1, string=f"Level: {level.current_level}")
        console.print(x=x + 1, y=y + 2, string=f"XP: {level.current_xp}")
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {level.experience_to_next_level}",
        )
        console.print(x=x + 1, y=y + 4, string=f"Attack: {fighter.power}")
        console.print(x=x + 1, y=y + 5, string=f"Defense: {fighter.defense}")


class LevelUpEventHandler(AskUserEventHandler):
    title = "Level Up"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(x=x, y=0, width=35, height=8, title=self.title,
                           clear=True, fg=color.white, bg=color.black)
        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")
        fighter = self.engine.player.fighter
        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {fighter.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {fighter.power})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {fighter.defense})",
        )

    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 2:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            else:
                player.level.increase_defense()
        else:
            self.engine.message_log.add_message("Invalid entry.",
                                                color.invalid)
            return None

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self,
        event: tcod.event.MouseButtonDown,
    ) -> Optional[ActionOrHandler]:
        return None


class InventoryEventHandler(AskUserEventHandler):
    title = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        player = self.engine.player
        num_inventory_items = len(player.inventory.items)
        height = num_inventory_items + 2

        if height <= 3:
            height = 3

        if player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0
        width = len(self.title) + 4
        console.draw_frame(x=x, y=y, width=width, height=height,
                           title=self.title, clear=True, fg=color.white,
                           bg=color.black)

        if num_inventory_items > 0:
            for i, item in enumerate(player.inventory.items):
                item_key = chr(ord("a") + i)
                is_equipped = player.equipment.item_is_equipped(item)
                item_string = f"({item_key}) {item.name}"

                if is_equipped:
                    item_string = f"{item_string} (E)"

                console.print(x + 1, y + i + 1, item_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    title = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if item.consumable:
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            return actions.EquipAction(self.engine.player, item)
        else:
            return None


class InventoryDropHandler(InventoryEventHandler):
    title = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
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

    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
    ) -> Optional[ActionOrHandler]:
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)

        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        return MainGameEventHandler(self.engine)


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
    def ev_keydown(self,
                   event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None
        key = event.sym
        modifier = event.mod
        player = self.engine.player

        if key == tcod.event.K_PERIOD and modifier & tcod.event.KMOD_SHIFT:
            return actions.TakeStairsAction(player)

        if key in move_keys:
            action = BumpAction(player, *move_keys[key])
        elif key in wait_keys:
            action = WaitAction(player)
        elif key == tcod.event.K_ESCAPE:
            raise SystemExit()
        elif key == tcod.event.K_v:
            return HistoryViewer(self.engine)
        elif key == tcod.event.K_g:
            action = PickupAction(player)
        elif key == tcod.event.K_i:
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.K_d:
            return InventoryDropHandler(self.engine)
        elif key == tcod.event.K_c:
            return CharacterScreenEventHandler(self.engine)
        elif key == tcod.event.K_SLASH:
            return LookHandler(self.engine)

        return action


class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")

        raise exceptions.QuitWithoutSaving()

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            self.on_quit()


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

    def ev_keydown(
        self,
        event: tcod.event.KeyDown,
    ) -> Optional[MainGameEventHandler]:
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
            return MainGameEventHandler(self.engine)

        return None
