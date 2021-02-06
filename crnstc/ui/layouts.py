from __future__ import annotations

from types import SimpleNamespace
from typing import (Iterable, Iterator, List, NamedTuple, Optional, Tuple,
                    TYPE_CHECKING)
import math
from dataclasses import dataclass

from crnstc.geometry import Vector, Rectangle, Position
from crnstc.utils import sum_or_zero, min_nonzero

if TYPE_CHECKING:
    from crnstc.ui.widgets import Widget

    DictList = List[dict]
    StretchyAllocationList = List["StretchyAllocation"]
    StretchyItemIterable = Iterable["StretchyItem"]
    Int2Tuple = Tuple[int, int]
    IntList = List[int]
    OptWidget = Optional[Widget]
    RectangleList = List[Rectangle]
    VectorList = List[Vector]
    WidgetIterator = Iterator[Widget]


class Layout:
    def aggregate_min_size(self, widget: Widget) -> Vector:
        raise NotImplementedError

    def aggregate_max_size(self, widget: Widget) -> Vector:
        raise NotImplementedError

    def calculate_layout(self, widget: Widget,
                         area: Rectangle) -> RectangleList:
        raise NotImplementedError


class SequentialLayout(Layout):
    def aggregate_min_size(self, widget: Widget) -> Vector:
        span_dim: int
        other_dim: int

        if isinstance(self, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif isinstance(self, VerticalLayout):
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

    def aggregate_max_size(self, widget: Widget) -> Vector:
        span_dim: int
        other_dim: int

        if isinstance(self, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif isinstance(self, VerticalLayout):
            # Child widgets will span the y dimension
            span_dim, other_dim = 1, 0
        else:
            raise NotImplementedError

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

    def calculate_layout(self, widget: Widget,
                         area: Rectangle) -> RectangleList:
        span_dim: int
        other_dim: int

        if isinstance(self, HorizontalLayout):
            # Child widgets will span the x dimension
            span_dim, other_dim = 0, 1
        elif isinstance(self, VerticalLayout):
            # Child widgets will span the y dimension
            span_dim, other_dim = 1, 0
        else:
            raise NotImplementedError

        stretchy_items: StretchyItemIterable = (
            StretchyItem(min_length=child.aggregate_min_size[span_dim],
                         max_length=child.aggregate_max_size[span_dim],
                         expansion=child.expansion[span_dim])
            for child
            in widget.children
        )

        allocations: StretchyAllocationList = allocate_stretchy(
            items=stretchy_items,
            available_length=area.dimensions[span_dim],
        )

        child_areas: RectangleList = list()

        for alloc in allocations:
            position = list(area.position)
            position[span_dim] += alloc.position_offset
            size = [0, 0]
            size[span_dim] = alloc.length
            size[other_dim] = area.dimensions[other_dim]
            child_areas.append(Rectangle(*position, *size))

        return child_areas


class HorizontalLayout(SequentialLayout):
    pass


class VerticalLayout(SequentialLayout):
    pass


@dataclass
class GridLayout(Layout):
    widget_columns: int = 2
    widget_rows: int = 2

    def aggregate_min_size(self, widget: Widget) -> Vector:
        width = sum(self._column_min_max_width(widget, column)[0]
                    for column in range(self.widget_columns))
        height = sum(self._row_min_max_height(widget, row)[0]
                     for row in range(self.widget_rows))
        return Vector(dx=width, dy=height)

    def aggregate_max_size(self, widget: Widget) -> Vector:
        width = sum_or_zero(self._column_min_max_width(widget, column)[1]
                            for column in range(self.widget_columns))
        height = sum_or_zero(self._row_min_max_height(widget, row)[1]
                             for row in range(self.widget_rows))
        return Vector(dx=width, dy=height)

    def _column_min_max_width(self, widget: Widget, column: int) -> Int2Tuple:
        minimums: IntList = list()
        maximums: IntList = list()

        for row in range(self.widget_rows):
            child: Widget = self.get_child_at_cell(widget=widget,
                                                   column=column, row=row)
            minimums.append(child.aggregate_min_size.dx)
            maximums.append(child.aggregate_max_size.dx)

        min_width: int = max(minimums)
        max_width: int = min_nonzero(maximums)

        # Maximum can't be smaller than minimum
        if max_width:
            max_width = max(min_width, max_width)

        return min_width, max_width

    def _row_min_max_height(self, widget: Widget, row: int) -> Int2Tuple:
        minimums: IntList = list()
        maximums: IntList = list()

        for column in range(self.widget_columns):
            child: Widget = self.get_child_at_cell(widget=widget,
                                                   column=column, row=row)
            minimums.append(child.aggregate_min_size.dy)
            maximums.append(child.aggregate_max_size.dy)

        min_height: int = max(minimums)
        max_height: int = min_nonzero(maximums)

        # Maximum can't be smaller than minimum
        if max_height:
            max_height = max(min_height, max_height)

        return min_height, max_height

    def calculate_layout(self, widget: Widget,
                         area: Rectangle) -> RectangleList:
        x_allocations: StretchyAllocationList = allocate_stretchy(
            items=self.get_x_stretchy_items(widget=widget),
            available_length=area.dimensions.dx)
        y_allocations: StretchyAllocationList = allocate_stretchy(
            items=self.get_y_stretchy_items(widget=widget),
            available_length=area.dimensions.dy)

        child_areas: RectangleList = list()

        for row in range(self.widget_rows):
            for column in range(self.widget_columns):
                x_alloc = x_allocations[column]
                y_alloc = y_allocations[row]
                position = area.relative(
                    x=x_alloc.position_offset,
                    y=y_alloc.position_offset,
                )
                child_areas.append(Rectangle(*position,
                                             w=x_alloc.length,
                                             h=y_alloc.length))

        return child_areas

    def get_child_at_cell(self, widget: Widget, column: int,
                          row: int) -> Widget:
        index = self.get_index(column=column, row=row)
        return widget.children[index]

    def get_children_in_row(self, widget: Widget, row: int) -> WidgetIterator:
        return (widget.children[i] for i in self.get_row_indexes(row=row))

    def get_children_in_column(self, widget: Widget,
                               column: int) -> WidgetIterator:
        return (widget.children[i]
                for i in self.get_column_indexes(column=column))

    def get_x_stretchy_items(self, widget: Widget) -> StretchyItemIterable:
        for column in range(self.widget_columns):
            min_width, max_width = self._column_min_max_width(widget=widget,
                                                              column=column)
            expansion = sum(
                child.expansion[0]
                for child
                in self.get_children_in_column(widget=widget, column=column)
            )
            yield StretchyItem(min_length=min_width,
                               max_length=max_width,
                               expansion=expansion)

    def get_y_stretchy_items(self, widget: Widget) -> StretchyItemIterable:
        for row in range(self.widget_rows):
            min_height, max_height = self._row_min_max_height(widget=widget,
                                                              row=row)
            expansion = sum(
                child.expansion[1]
                for child
                in self.get_children_in_row(widget=widget, row=row)
            )
            yield StretchyItem(min_length=min_height,
                               max_length=max_height,
                               expansion=expansion)

    def get_cell(self, index: int) -> Int2Tuple:
        column = index % self.widget_columns
        row = index // self.widget_columns
        return column, row

    def get_index(self, column: int, row: int) -> int:
        return row * self.widget_columns + column

    def get_row_indexes(self, row: int) -> range:
        return range(self.get_index(column=0, row=row),
                     self.get_index(column=0, row=row + 1))

    def get_column_indexes(self, column: int) -> range:
        return range(self.get_index(column=column, row=0),
                     self.widget_columns * self.widget_rows,
                     self.widget_columns)


class StretchyItem(NamedTuple):
    min_length: int
    max_length: int
    expansion: float


class StretchyAllocation(NamedTuple):
    position_offset: int
    length: int


def allocate_stretchy(items: StretchyItemIterable,
                      available_length: int) -> StretchyAllocationList:
    calcs = list()
    remaining_length: int = available_length
    remaining_expansion: float = 0.0

    for index, item in enumerate(items):
        calcs.append(SimpleNamespace(
            index=index,
            item=item,
            length=item.min_length,
        ))
        remaining_length -= item.min_length
        remaining_expansion += item.expansion

    if remaining_length > 0:
        # Sort items in a way that lets us do everything in one pass
        def calcs_sort_key(calc):
            # Treat zero as infinite
            max_length = calc.item.max_length or math.inf
            # Items most likely to hit max_length go first
            primary = max_length / calc.item.expansion
            # Among the remainder, higher expansion goes first
            secondary = -calc.item.expansion
            return primary, secondary
        calcs.sort(key=calcs_sort_key)

        for calc in calcs:
            percentage: float = calc.item.expansion / remaining_expansion
            add_length: int = math.ceil(remaining_length * percentage)
            max_add = (calc.item.max_length or math.inf) - calc.length
            add_length = min(add_length, max_add)
            calc.length += add_length
            remaining_length -= add_length
            remaining_expansion -= calc.item.expansion

        # Put everything back in order
        calcs.sort(key=lambda c: c.index)

    position_offset = 0
    allocations: StretchyAllocationList = list()

    for calc in calcs:
        allocations.append(StretchyAllocation(
            position_offset=position_offset,
            length=calc.length,
        ))
        position_offset += calc.length

    return allocations
