from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import math

from crnstc import actions
from crnstc import color
from crnstc.components.inventory import Inventory
from crnstc.components.base_component import BaseComponent
from crnstc.exceptions import Impossible
from crnstc.input_handlers import ActionOrHandler, AreaRangedAttackHandler

if TYPE_CHECKING:
    from crnstc.entity import Actor, Item


class Consumable(BaseComponent):
    parent: Item

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        return actions.ItemAction(consumer, self.parent)

    def activate(self, action: actions.ItemAction) -> None:
        raise NotImplementedError()

    def consume(self) -> None:
        entity = self.parent
        inventory = entity.parent
        if isinstance(inventory, Inventory):
            inventory.items.remove(entity)


@dataclass
class HealingConsumable(Consumable):
    amount: int

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fighter.heal(self.amount)

        if amount_recovered > 0:
            self.engine.message_log.add_message(
                f"You use the {self.parent.name}, and recover"
                f" {amount_recovered} HP!",
                color.health_recovered,
            )
            self.consume()
        else:
            raise Impossible("Your health is already full.")


@dataclass
class ExplosiveConsumable(Consumable):
    damage: int
    max_range: int
    blast_reduction: int
    radius: int = field(init=False)

    def __post_init__(self):
        self.radius = math.ceil(float(self.damage) / self.blast_reduction) - 1

    def get_action(self, consumer: Actor) -> AreaRangedAttackHandler:
        self.engine.message_log.add_message("Select a target location.",
                                            color.needs_target)
        return AreaRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
            radius=self.radius,
        )

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target_position = action.target_position
        assert target_position is not None

        if not self.engine.game_map.visible[action.target_position]:
            raise Impossible("You can't target an area that you can't see.")

        if consumer.position.distance(target_position) > self.max_range:
            raise Impossible("Target out of range.")

        self.engine.message_log.add_message(
            f"The {self.parent.name} explodes!"
        )

        targets_hit = False

        for actor in self.engine.game_map.actors:
            distance = actor.position.distance(target_position)

            if distance > self.radius:
                continue

            reduction = math.floor(distance * self.blast_reduction)
            blast_damage = self.damage - reduction

            if blast_damage and actor is not consumer:
                targets_hit = True

            damage_taken = blast_damage - actor.fighter.defense
            self.engine.message_log.add_message(
                f"{actor.name} is caught in the blast!"
                f" {damage_taken} damage."
            )
            actor.fighter.take_damage(damage_taken)

        if not targets_hit:
            raise Impossible("No targets in blast radius.")

        self.consume()
