from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from crnstc import color
from crnstc import exceptions
from crnstc.geometry import Position, Vector

if TYPE_CHECKING:
    from crnstc.engine import Engine
    from crnstc.entity import Entity, Actor, Item


@dataclass
class Action:
    entity: Actor

    @property
    def engine(self) -> Engine:
        game_map = self.entity.game_map
        assert game_map is not None
        return game_map.engine

    def perform(self) -> None:
        raise NotImplementedError()


class PickupAction(Action):
    def perform(self) -> None:
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if self.entity.position == item.position:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")

                self.engine.game_map.entities.remove(item)
                item.parent = self.entity.inventory
                inventory.items.append(item)
                self.engine.message_log.add_message("You picked up the"
                                                    f" {item.name}.")
                return

        raise exceptions.Impossible("There is nothing here to pick up.")


@dataclass
class ItemAction(Action):
    item: Item
    target_position: Optional[Position] = None

    def __post_init__(self):
        if not self.target_position:
            self.target_position = self.entity.position

    @property
    def target_actor(self) -> Optional[Actor]:
        assert self.target_position is not None
        return self.engine.game_map.get_actor_at(self.target_position)

    def perform(self) -> None:
        if self.item.consumable:
            self.item.consumable.activate(self)


class DropItem(ItemAction):
    def perform(self) -> None:
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)

        self.entity.inventory.drop(self.item)


@dataclass
class EquipAction(Action):
    item: Item

    def perform(self) -> None:
        self.entity.equipment.toggle_equip(self.item)


class WaitAction(Action):
    def perform(self) -> None:
        pass


class TakeStairsAction(Action):
    def perform(self) -> None:
        down_stairs_location = self.engine.game_map.down_stairs_location

        if self.entity.position == down_stairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You proceed further into the facility.",
                color.descend,
            )


@dataclass
class ActionWithDirection(Action):
    direction: Vector

    @property
    def destination(self) -> Position:
        return self.entity.position + self.direction

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.engine.game_map.get_blocker(self.destination)

    @property
    def target_actor(self) -> Optional[Actor]:
        return self.engine.game_map.get_actor_at(self.destination)


class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.target_actor

        if not target:
            raise exceptions.Impossible("Nothing to attack.")

        damage = self.entity.fighter.power - target.fighter.defense
        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if self.entity is self.engine.player:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk

        if damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} hit points.",
                attack_color,
            )
            target.fighter.hp -= damage
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.",
                attack_color,
            )


class MovementAction(ActionWithDirection):
    def perform(self) -> None:

        if not self.engine.game_map.in_bounds(self.destination):
            raise exceptions.Impossible("That way is blocked.")

        if not self.engine.game_map.tiles["walkable"][self.destination]:
            raise exceptions.Impossible("That way is blocked.")

        if self.engine.game_map.get_blocker(self.destination):
            raise exceptions.Impossible("That way is blocked.")

        self.entity.move(self.direction)


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(entity=self.entity,
                               direction=self.direction).perform()
        else:
            return MovementAction(entity=self.entity,
                                  direction=self.direction).perform()
