"""General-purpose utility functions."""
from typing import Iterable


IntIterable = Iterable[int]


def clamp(low, x, high):
    """
    Clamp the specified value between a lower and upper bound.

    Args:
        low: The lower boundary. If x is less than low, low will be returned.
        x: The value to clamp.
        high: The upper boundary. If x is greater than high, high will be
            returned.

    Returns:
        The clamped value.

    """
    return max(low, min(x, high))


def sum_or_zero(iterable: IntIterable) -> int:
    """
    Return zero if any element of the specified iterable is zero, otherwise
    return the sum of the elements. Useful when treating zero as an "unlimited"
    value.

    Args:
        iterable: The elements to sum.

    Returns:
        The sum, or zero.

    """
    if 0 in iterable:
        return 0
    else:
        return sum(iterable)


def min_nonzero(iterable: IntIterable) -> int:
    """
    Return the lowest nonzero value in the specified iterable. Useful when
    treating zero as an "unlimited" value.

    Args:
        iterable: The elements to compare.

    Returns:
        The lowest nonzero value.

    """
    if any(iterable):
        return min(i for i in iterable if i != 0)
    else:
        return 0
