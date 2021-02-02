from __future__ import annotations

from typing import List, Iterable, TYPE_CHECKING
import math


from crnstc.geometry import Vector, Rectangle, Position

if TYPE_CHECKING:
    from crnstc.ui.widgets import Widget


RectangleList = List[Rectangle]
VectorList = List[Vector]
IntIterable = Iterable[int]
IntList = List[int]
DictList = List[dict]


class Layout:
    @classmethod
    def aggregate_min_size(cls, widget: Widget) -> Vector:
        raise NotImplementedError

    @classmethod
    def aggregate_max_size(cls, widget: Widget) -> Vector:
        raise NotImplementedError

    @classmethod
    def calculate_layout(cls, widget: Widget,
                         area: Rectangle) -> RectangleList:
        raise NotImplementedError


class SequentialLayout(Layout):
    @classmethod
    def aggregate_min_size(cls, widget: Widget) -> Vector:
        span_dim: int
        other_dim: int

        if issubclass(cls, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif issubclass(cls, VerticalLayout):
            # Child widgets will span the y dimension
            span_dim, other_dim = 1, 0
        else:
            raise NotImplementedError

        min_sizes: VectorList = [child.aggregate_min_size
                                 for child in widget.children]
        agg_min: IntList = [0, 0]
        agg_min[span_dim] = sum(min_size[span_dim] for min_size in min_sizes)
        agg_min[other_dim] = max(min_size[other_dim] for min_size in min_sizes)

        # Check if the min size of the parent widget is larger than the min
        # size of its children
        agg_min[span_dim] = max(agg_min[span_dim], widget.min_size[span_dim])
        agg_min[other_dim] = max(agg_min[other_dim],
                                 widget.min_size[other_dim])

        return Vector(*agg_min)

    @classmethod
    def aggregate_max_size(cls, widget: Widget) -> Vector:
        span_dim: int
        other_dim: int

        if issubclass(cls, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif issubclass(cls, VerticalLayout):
            # Child widgets will span the y dimension
            span_dim, other_dim = 1, 0
        else:
            raise NotImplementedError

        # Zero is infinity, so a sum including zero is also infinity
        def sum_or_zero(iterable: IntIterable) -> int:
            if 0 in iterable:
                return 0
            else:
                return sum(iterable)

        # Ignore zero (infinity) when looking for the smallest value, unless
        # they're all zero
        def min_nonzero(iterable: IntIterable) -> int:
            if any(iterable):
                return min(i for i in iterable if i != 0)
            else:
                return 0

        max_sizes: VectorList = [child.aggregate_max_size
                                 for child in widget.children]
        agg_max: IntList = [0, 0]
        agg_max[span_dim] = sum_or_zero(max_size[span_dim]
                                        for max_size in max_sizes)
        agg_max[other_dim] = min_nonzero(max_size[span_dim]
                                         for max_size in max_sizes)

        # Check if the max size of the parent widget is smaller than the max
        # size of its children
        agg_max[span_dim] = min_nonzero((agg_max[span_dim],
                                         widget.max_size[span_dim]))
        agg_max[other_dim] = min_nonzero((agg_max[other_dim],
                                          widget.max_size[other_dim]))

        # Aggregate max size can't be smaller than aggregate min size
        min_size: Vector = widget.aggregate_min_size

        for dim, value in enumerate(agg_max):
            if value:
                agg_max[dim] = max(value, min_size[dim])

        return Vector(*agg_max)

    @classmethod
    def calculate_layout(cls, widget: Widget,
                         area: Rectangle) -> RectangleList:
        span_dim: int
        other_dim: int

        if issubclass(cls, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif issubclass(cls, VerticalLayout):
            # Child widgets will span the y dimension
            span_dim, other_dim = 1, 0
        else:
            raise NotImplementedError

        calcs: DictList = [{
            "index": i,
            "child": child,
            "span": child.aggregate_min_size[span_dim],
            "max_span": child.aggregate_max_size[span_dim],
        } for i, child in enumerate(widget.children)]

        remaining_span: int = area.dimensions[span_dim] - sum(c["span"]
                                                              for c in calcs)

        if remaining_span > 0:
            # Sort children in a way that lets us do everything in one pass
            def calcs_sort_key(calc):
                expansion = calc["child"].expansion[span_dim]
                # Treat zero as infinite
                max_span = calc["max_span"] or math.inf
                # Children most likely to hit max_span go first
                primary = max_span / expansion
                # Among the remainder, higher expansion goes first
                secondary = -expansion
                return primary, secondary
            calcs.sort(key=calcs_sort_key)

            # Total of all expansion weights among children, reduced as each
            # child gets its allocation
            remaining_expansion: float = sum(child.expansion[span_dim]
                                             for child in widget.children)

            for calc in calcs:
                expansion: float = calc["child"].expansion[span_dim]
                percentage: float = expansion / remaining_expansion
                add_span: int = math.ceil(remaining_span * percentage)
                add_span = min(add_span,
                               (calc["max_span"] or math.inf) - calc["span"])
                calc["span"] += add_span
                remaining_span -= add_span
                remaining_expansion -= expansion

            # Put everything back in order
            calcs.sort(key=lambda c: c["index"])

        child_areas: RectangleList = list()
        next_position: Position = area.position

        for calc in calcs:
            size: IntList = [0, 0]
            size[span_dim] = calc["span"]
            size[other_dim] = area.dimensions[other_dim]
            child_areas.append(Rectangle(*next_position, *size))

            shift: IntList = [0, 0]
            shift[span_dim] = size[span_dim]
            next_position = next_position.relative(*shift)

        return child_areas


class HorizontalLayout(SequentialLayout):
    pass


class VerticalLayout(SequentialLayout):
    pass
