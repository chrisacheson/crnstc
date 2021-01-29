from crnstc.components.ai import BaseAI, HostileEnemy
from crnstc.components import consumable, equippable
from crnstc.components.equipment import Equipment
from crnstc.components.fighter import Fighter
from crnstc.components.inventory import Inventory
from crnstc.components.level import Level
from crnstc.entity import Actor, Item
from crnstc import color

player = Actor(
    char="@",
    color=color.white,
    name="Player",
    ai_cls=BaseAI,
    equipment=Equipment(),
    fighter=Fighter(max_hp=30, base_defense=1, base_power=2),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=200),
)

corpsec_guard = Actor(
    char="p",
    color=color.blue,
    name="CorpSec Guard",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(max_hp=10, base_defense=0, base_power=3),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
)
combat_drone = Actor(
    char="D",
    color=color.green,
    name="Combat Drone",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(max_hp=16, base_defense=1, base_power=4),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
)

medkit = Item(char="!", color=color.bright_purple, name="Medkit",
              consumable=consumable.HealingConsumable(amount=4))
grenade = Item(
    char="*",
    color=color.green,
    name="Grenade",
    consumable=consumable.ExplosiveConsumable(damage=15, max_range=5,
                                              blast_reduction=5),
)

combat_knife = Item(char="/", color=color.deep_sky_blue, name="Combat Knife",
                    equippable=equippable.CombatKnife())
telescoping_baton = Item(char="/", color=color.deep_sky_blue,
                         name="Telescoping Baton",
                         equippable=equippable.TelescopingBaton())
kevlar_vest = Item(char="[", color=color.flat_dark_earth, name="Kevlar Vest",
                   equippable=equippable.KevlarVest())
ballistic_plate_armor = Item(char="[", color=color.flat_dark_earth,
                             name="Ballistic Plate Armor",
                             equippable=equippable.BallisticPlateArmor())
