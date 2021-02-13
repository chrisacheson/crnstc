"""Input handling."""
from types import SimpleNamespace
from typing import Callable, Dict, Iterable, List, NamedTuple, Optional, Set

import tcod.event as te


InputCallbackFunction = Callable[[object], None]


class KeyStroke(NamedTuple):
    """
    Represents a keystroke along with any active modifier keys.

    Args:
        sym: The tcod symbol code of the key.
        mod_shift: True if shift is held. Defaults to False.
        mod_ctrl: True if ctrl is held. Defaults to False.
        mod_alt: True if alt is held. Defaults to False.

    """
    sym: int
    mod_shift: bool = False
    mod_ctrl: bool = False
    mod_alt: bool = False

    @property
    def char(self) -> str:
        """The character that should be produced by this keystroke."""
        if self.mod_ctrl or self.mod_alt:
            raise ValueError

        if self.sym < te.K_a or self.sym > te.K_z:
            raise NotImplementedError

        char: str = chr(ord("a") + self.sym - te.K_a)

        if self.mod_shift:
            char = char.upper()

        return char

    @classmethod
    def from_tcod_event(cls, event: te.KeyboardEvent) -> "KeyStroke":
        """
        Create a KeyStroke from a tcod event.

        Args:
            event: The tcod event.

        Returns:
            The new KeyStroke.

        """
        return KeyStroke(
            sym=event.sym,
            mod_shift=bool(event.mod & te.KMOD_SHIFT),
            mod_ctrl=bool(event.mod & te.KMOD_CTRL),
            mod_alt=bool(event.mod & te.KMOD_ALT),
        )

    @classmethod
    def from_letter(cls, letter: str) -> "KeyStroke":
        """
        Create a KeyStroke that would produce the specified letter.

        Args:
            letter: An upper or lower case letter.

        Returns:
            The new KeyStroke.

        """
        return KeyStroke(
            sym=te.K_a + ord(letter.lower()) - ord("a"),
            mod_shift=letter.isupper(),
        )


KeyStrokeIterable = Iterable[KeyStroke]
KeyStrokeSet = Set[KeyStroke]


keysets = SimpleNamespace(
    north_keys=frozenset((
        KeyStroke(te.K_UP),
        KeyStroke(te.K_KP_8),
        KeyStroke(te.K_k),
    )),
    south_keys=frozenset((
        KeyStroke(te.K_DOWN),
        KeyStroke(te.K_KP_2),
        KeyStroke(te.K_j),
    )),
    west_keys=frozenset((
        KeyStroke(te.K_LEFT),
        KeyStroke(te.K_KP_4),
        KeyStroke(te.K_h),
    )),
    east_keys=frozenset((
        KeyStroke(te.K_RIGHT),
        KeyStroke(te.K_KP_6),
        KeyStroke(te.K_l),
    )),
    northwest_keys=frozenset((
        KeyStroke(te.K_HOME),
        KeyStroke(te.K_KP_7),
        KeyStroke(te.K_y),
    )),
    southwest_keys=frozenset((
        KeyStroke(te.K_END),
        KeyStroke(te.K_KP_1),
        KeyStroke(te.K_b),
    )),
    northeast_keys=frozenset((
        KeyStroke(te.K_PAGEUP),
        KeyStroke(te.K_KP_9),
        KeyStroke(te.K_u),
    )),
    southeast_keys=frozenset((
        KeyStroke(te.K_PAGEDOWN),
        KeyStroke(te.K_KP_3),
        KeyStroke(te.K_n),
    )),
    wait_keys=frozenset((
        KeyStroke(te.K_PERIOD),
        KeyStroke(te.K_KP_5),
        KeyStroke(te.K_CLEAR),
    )),
    confirm_keys=frozenset((
        KeyStroke(te.K_RETURN),
        KeyStroke(te.K_KP_ENTER),
    )),
)

keysets.x_axis_keys = keysets.west_keys | keysets.east_keys
keysets.y_axis_keys = keysets.north_keys | keysets.south_keys
keysets.cardinal_keys = keysets.x_axis_keys | keysets.y_axis_keys
keysets.diagonal_keys = (keysets.northwest_keys | keysets.southwest_keys |
                         keysets.northeast_keys | keysets.southeast_keys)
keysets.compass_keys = keysets.cardinal_keys | keysets.diagonal_keys


class InputCallback(NamedTuple):
    """
    A callback function along with data to be passed to it.

    Args:
        function: The callback function.
        data: Optional data to pass to the function when it is called.

    """
    function: InputCallbackFunction
    data: object = None


InputCallbackDict = Dict[KeyStroke, InputCallback]
OptInputCallback = Optional[InputCallback]


class InputReceiverMixin:
    """
    Mixin class for making a widget capable of receiving input.

    Keystroke objects can be added to the blocked_keys attribute to prevent
    lower-priority widgets from receiving them while this widget remains
    registered.

    """
    def __init__(self, *args, **kwargs) -> None:
        self.blocked_keys: KeyStrokeSet = set()
        self.bound_keys: InputCallbackDict = dict()
        # https://github.com/python/mypy/issues/5887
        super().__init__(*args, **kwargs)  # type: ignore

    def bind_keyset(self, keyset: KeyStrokeIterable,
                    function: InputCallbackFunction,
                    data: object = None) -> None:
        """
        Bind a set of keys to a callback.

        Args:
            function: The function to be called when one of the keys in the
                keyset is pressed.
            data: Optional data to pass to the function.

        """
        for keystroke in keyset:
            self.bound_keys[keystroke] = InputCallback(function=function,
                                                       data=data)


InputReceiverMixinList = List[InputReceiverMixin]


class InputHandler(te.EventDispatch[None]):
    """
    Main input handling class.

    Widgets interested in receiving input should inherit the
    InputReceiverMixin, and then should be registered with the register()
    method.

    Keystrokes will be routed to the most recently registered receiver first.
    The bound_keys and blocked_keys attributes of each receiver will be checked
    for a matching keystroke, stopping when one is found.

    """
    def __init__(self) -> None:
        self.receivers: InputReceiverMixinList = list()

    def register(self, receiver: InputReceiverMixin) -> None:
        """
        Register a widget to receive input.

        Args:
            receiver: The receiving widget.

        """
        self.receivers.append(receiver)

    def unregister(self, receiver: InputReceiverMixin) -> None:
        """
        Stop a widget from receiving further input.

        Args:
            receiver: The receiving widget.

        """
        self.receivers.remove(receiver)

    def ev_keydown(self, event: te.KeyDown) -> None:
        keystroke = KeyStroke.from_tcod_event(event)

        # Most recently added receiver has priority
        for receiver in reversed(self.receivers):
            if keystroke in receiver.blocked_keys:
                return

            callback = receiver.bound_keys.get(keystroke)

            if callback:
                callback.function(callback.data)
                return
