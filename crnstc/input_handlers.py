from __future__ import annotations

import os
from typing import Callable, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass

import tcod.event

from crnstc import actions
from crnstc.actions import Action, BumpAction, WaitAction, PickupAction
from crnstc import color
from crnstc import exceptions
from crnstc.utils import clamp
from crnstc.geometry import compass, Position, Rectangle

if TYPE_CHECKING:
    from crnstc.engine import Engine
    from crnstc.entity import Item


move_keys = {
    # Arrow keys
    tcod.event.K_UP: compass.north,
    tcod.event.K_DOWN: compass.south,
    tcod.event.K_LEFT: compass.west,
    tcod.event.K_RIGHT: compass.east,
    tcod.event.K_HOME: compass.northwest,
    tcod.event.K_END: compass.southwest,
    tcod.event.K_PAGEUP: compass.northeast,
    tcod.event.K_PAGEDOWN: compass.southeast,
    # Numpad keys
    tcod.event.K_KP_1: compass.southwest,
    tcod.event.K_KP_2: compass.south,
    tcod.event.K_KP_3: compass.southeast,
    tcod.event.K_KP_4: compass.west,
    tcod.event.K_KP_6: compass.east,
    tcod.event.K_KP_7: compass.northwest,
    tcod.event.K_KP_8: compass.north,
    tcod.event.K_KP_9: compass.northeast,
    # Vi keys
    tcod.event.K_h: compass.west,
    tcod.event.K_j: compass.south,
    tcod.event.K_k: compass.north,
    tcod.event.K_l: compass.east,
    tcod.event.K_y: compass.northwest,
    tcod.event.K_u: compass.northeast,
    tcod.event.K_b: compass.southwest,
    tcod.event.K_n: compass.southeast,
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
        position = Position(*event.tile)

        if self.engine.game_map.in_bounds(position):
            self.engine.mouse_location = position

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

        dialog_box = Rectangle(x=0, y=0, w=len(self.title) + 4, h=7)

        if self.engine.player.position.x <= 30:
            dialog_box = dialog_box.move(dx=40, dy=0)

        console.draw_frame(*dialog_box, title=self.title, clear=True,
                           fg=color.white, bg=color.black)
        level = self.engine.player.level
        fighter = self.engine.player.fighter
        strings = [
            f"Level: {level.current_level}",
            f"XP: {level.current_xp}",
            f"XP for next Level: {level.experience_to_next_level}",
            f"Attack: {fighter.power}",
            f"Defense: {fighter.defense}",
        ]
        text_position = dialog_box.relative(x=1, y=1)

        for string in strings:
            console.print(*text_position, string=string)
            text_position += compass.south


class LevelUpEventHandler(AskUserEventHandler):
    title = "Level Up"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        dialog_box = Rectangle(x=0, y=0, w=35, h=8)

        if self.engine.player.position.x <= 30:
            dialog_box = dialog_box.move(dx=40, dy=0)

        console.draw_frame(*dialog_box, title=self.title, clear=True,
                           fg=color.white, bg=color.black)
        fighter = self.engine.player.fighter
        strings = [
            "Congratulations! You level up!",
            "Select an attribute to increase.",
            "",
            f"a) Constitution (+20 HP, from {fighter.max_hp})",
            f"b) Strength (+1 attack, from {fighter.power})",
            f"c) Agility (+1 defense, from {fighter.defense})",
        ]
        text_position = dialog_box.relative(x=1, y=1)

        for string in strings:
            console.print(*text_position, string=string)
            text_position += compass.south

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

        dialog_box = Rectangle(x=0, y=0, w=len(self.title) + 4, h=height)

        if player.position.x <= 30:
            dialog_box = dialog_box.move(dx=40, dy=0)

        console.draw_frame(*dialog_box, title=self.title, clear=True,
                           fg=color.white, bg=color.black)
        text_position = dialog_box.relative(x=1, y=1)

        if num_inventory_items > 0:
            for i, item in enumerate(player.inventory.items):
                item_key = chr(ord("a") + i)
                is_equipped = player.equipment.item_is_equipped(item)
                item_string = f"({item_key}) {item.name}"

                if is_equipped:
                    item_string = f"{item_string} (E)"

                console.print(*text_position, item_string)
                text_position += compass.south
        else:
            console.print(*text_position, "(Empty)")

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
        self.engine.mouse_location = player.position

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        pos = self.engine.mouse_location
        console.tiles_rgb["bg"][pos] = color.white
        console.tiles_rgb["fg"][pos] = color.black

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

            position = self.engine.mouse_location
            vector = move_keys[key]
            position += vector * modifier
            position = self.engine.game_map.shape.clamp(position)
            self.engine.mouse_location = position
            return None
        elif key in confirm_keys:
            return self.on_index_selected(self.engine.mouse_location)

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self,
        event: tcod.event.MouseButtonDown,
    ) -> Optional[ActionOrHandler]:

        position = Position(*event.tile)

        if self.engine.game_map.in_bounds(position):
            if event.button == 1:
                return self.on_index_selected(position)

        return super().ev_mousebuttondown(event)

    def on_index_selected(self,
                          position: Position) -> Optional[ActionOrHandler]:
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    def on_index_selected(self, position: Position) -> MainGameEventHandler:
        return MainGameEventHandler(self.engine)


@dataclass
class RangedAttackHandler(SelectIndexHandler):
    callback: Callable[[Position], Optional[Action]]

    def on_index_selected(self, position: Position) -> Optional[Action]:
        # https://github.com/python/mypy/issues/5485
        return self.callback(position)  # type: ignore


@dataclass
class AreaRangedAttackHandler(RangedAttackHandler):
    radius: int

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        diameter = self.radius * 2 + 1
        area = Rectangle(x=0, y=0, w=diameter, h=diameter)
        area = area.center_on(self.engine.mouse_location)
        console.draw_frame(*area, fg=color.red, clear=False)


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
            action = BumpAction(player, move_keys[key])
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
        dialog_box = Rectangle(x=0, y=0, w=console.width, h=console.height)
        dialog_box = dialog_box.grow(-3)
        console.draw_frame(*dialog_box, title="Message History", clear=True,
                           fg=color.white, bg=color.black)
        text_area = dialog_box.grow(-1)
        self.engine.message_log.render_messages(
            console,
            text_area,
            self.engine.message_log.messages[: self.cursor + 1],
        )

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
