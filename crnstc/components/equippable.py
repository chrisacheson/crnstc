from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Item


@dataclass
class Equippable(BaseComponent):
    parent: Item = field(init=False)
    equipment_type: EquipmentType
    power_bonus: int = 0
    defense_bonus: int = 0


@dataclass
class CombatKnife(Equippable):
    equipment_type: EquipmentType = EquipmentType.weapon
    power_bonus: int = 2


@dataclass
class TelescopingBaton(Equippable):
    equipment_type: EquipmentType = EquipmentType.weapon
    power_bonus: int = 4


@dataclass
class KevlarVest(Equippable):
    equipment_type: EquipmentType = EquipmentType.armor
    defense_bonus: int = 1


@dataclass
class BallisticPlateArmor(Equippable):
    equipment_type: EquipmentType = EquipmentType.armor
    defense_bonus: int = 3
