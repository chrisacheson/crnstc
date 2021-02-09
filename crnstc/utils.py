"""General-purpose utility functions."""


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
