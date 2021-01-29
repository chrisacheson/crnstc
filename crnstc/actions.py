from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from crnstc import color
from crnstc import exceptions

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
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if actor_location_x == item.x and actor_location_y == item.y:
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
    target_xy: Optional[Tuple[int, int]] = None

    def __post_init__(self):
        if not self.target_xy:
            self.target_xy = self.entity.x, self.entity.y

    @property
    def target_actor(self) -> Optional[Actor]:
        assert self.target_xy is not None
        return self.engine.game_map.get_actor_at(*self.target_xy)

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

        if (self.entity.x, self.entity.y) == down_stairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You proceed further into the facility.",
                color.descend,
            )


@dataclass
class ActionWithDirection(Action):
    dx: int
    dy: int

    @property
    def dest_xy(self) -> Tuple[int, int]:
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.engine.game_map.get_blocker(*self.dest_xy)

    @property
    def target_actor(self) -> Optional[Actor]:
        return self.engine.game_map.get_actor_at(*self.dest_xy)


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
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(x=dest_x, y=dest_y):
            raise exceptions.Impossible("That way is blocked.")

        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            raise exceptions.Impossible("That way is blocked.")

        if self.engine.game_map.get_blocker(x=dest_x, y=dest_y):
            raise exceptions.Impossible("That way is blocked.")

        self.entity.move(dx=self.dx, dy=self.dy)


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(entity=self.entity,
                               dx=self.dx, dy=self.dy).perform()
        else:
            return MovementAction(entity=self.entity,
                                  dx=self.dx, dy=self.dy).perform()
