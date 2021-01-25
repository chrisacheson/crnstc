from components.ai import BaseAI, HostileEnemy
from components.fighter import Fighter
from entity import Actor
import color

player = Actor(char="@", color=color.white, name="Player", ai_cls=BaseAI,
               fighter=Fighter(max_hp=30, defense=2, power=5))

corpsec_guard = Actor(char="p", color=color.blue, name="CorpSec Guard",
                      ai_cls=HostileEnemy,
                      fighter=Fighter(max_hp=10, defense=0, power=3))
corpsec_soldier = Actor(char="p", color=color.green, name="CorpSec Soldier",
                        ai_cls=HostileEnemy,
                        fighter=Fighter(max_hp=16, defense=1, power=4))
