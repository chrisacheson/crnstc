from entity import Entity
from colors import Colors

player = Entity(char="@", color=Colors.white, name="Player",
                blocks_movement=True)

corpsec_guard = Entity(char="p", color=Colors.blue, name="CorpSec Guard",
                       blocks_movement=True)
corpsec_soldier = Entity(char="p", color=Colors.green, name="CorpSec Soldier",
                         blocks_movement=True)
