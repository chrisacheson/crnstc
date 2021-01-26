from components.ai import BaseAI, HostileEnemy
from components import consumable
from components.fighter import Fighter
from components.inventory import Inventory
from entity import Actor, Item
import color

player = Actor(char="@", color=color.white, name="Player", ai_cls=BaseAI,
               fighter=Fighter(max_hp=30, defense=2, power=5),
               inventory=Inventory(capacity=26))

corpsec_guard = Actor(char="p", color=color.blue, name="CorpSec Guard",
                      ai_cls=HostileEnemy,
                      fighter=Fighter(max_hp=10, defense=0, power=3),
                      inventory=Inventory(capacity=0))
combat_drone = Actor(char="D", color=color.green, name="Combat Drone",
                     ai_cls=HostileEnemy,
                     fighter=Fighter(max_hp=16, defense=1, power=4),
                     inventory=Inventory(capacity=0))

medkit = Item(char="!", color=color.bright_purple, name="Medkit",
              consumable=consumable.HealingConsumable(amount=4))
grenade = Item(
    char="*",
    color=color.green,
    name="Grenade",
    consumable=consumable.ExplosiveConsumable(damage=15, max_range=5,
                                              blast_reduction=5),
)
