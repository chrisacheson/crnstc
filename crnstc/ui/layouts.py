from __future__ import annotations

from typing import Iterator, List, Optional, Tuple, TYPE_CHECKING
import math
from dataclasses import dataclass

from crnstc.geometry import Vector, Rectangle, Position
from crnstc.utils import sum_or_zero, min_nonzero

if TYPE_CHECKING:
    from crnstc.ui.widgets import Widget

    RectangleList = List[Rectangle]
    VectorList = List[Vector]
    IntList = List[int]
    Int2Tuple = Tuple[int, int]
    DictList = List[dict]
    OptWidget = Optional[Widget]
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
        column_calcs: DictList = list()
        remaining_width: int = area.dimensions.dx
        remaining_width_expansion: float = 0.0

        for column in range(self.widget_columns):
            min_width, max_width = self._column_min_max_width(widget=widget,
                                                              column=column)
            remaining_width -= min_width
            width_expansion = sum(
                child.expansion[0]
                for child
                in self.get_children_in_column(widget=widget, column=column)
            )
            remaining_width_expansion += width_expansion
            column_calcs.append({
                "column": column,
                "width": min_width,
                "max_width": max_width,
                "width_expansion": width_expansion,
            })

        if remaining_width > 0:
            # Sort columns in a way that lets us do everything in one pass
            def columns_sort_key(calc):
                # Treat zero as infinite
                max_width = calc["max_width"] or math.inf
                # Columns most likely to hit max_width go first
                primary = max_width / calc["width_expansion"]
                # Among the remainder, higher expansion goes first
                secondary = -calc["width_expansion"]
                return primary, secondary
            column_calcs.sort(key=columns_sort_key)

            for calc in column_calcs:
                w_exp: float = calc["width_expansion"]
                w_percentage: float = w_exp / remaining_width_expansion
                add_width: int = math.ceil(remaining_width * w_percentage)
                max_add = (calc["max_width"] or math.inf) - calc["width"]
                add_width = min(add_width, max_add)
                calc["width"] += add_width
                remaining_width -= add_width
                remaining_width_expansion -= w_exp

            # Put everything back in order
            column_calcs.sort(key=lambda c: c["column"])

        x = area.position.x

        for calc in column_calcs:
            calc["x"] = x
            x += calc["width"]

        row_calcs: DictList = list()
        remaining_height: int = area.dimensions.dy
        remaining_height_expansion: float = 0.0

        for row in range(self.widget_rows):
            min_height, max_height = self._row_min_max_height(widget=widget,
                                                              row=row)
            remaining_height -= min_height
            height_expansion = sum(
                child.expansion[1]
                for child
                in self.get_children_in_row(widget=widget, row=row)
            )
            remaining_height_expansion += height_expansion
            row_calcs.append({
                "row": row,
                "height": min_height,
                "max_height": max_height,
                "height_expansion": height_expansion,
            })

        if remaining_height > 0:
            # Sort rows in a way that lets us do everything in one pass
            def rows_sort_key(calc):
                # Treat zero as infinite
                max_height = calc["max_height"] or math.inf
                # Rows most likely to hit max_height go first
                primary = max_height / calc["height_expansion"]
                # Among the remainder, higher expansion goes first
                secondary = -calc["height_expansion"]
                return primary, secondary
            row_calcs.sort(key=rows_sort_key)

            for calc in row_calcs:
                h_exp: float = calc["height_expansion"]
                h_percentage: float = h_exp / remaining_height_expansion
                add_height: int = math.ceil(remaining_height * h_percentage)
                max_add = (calc["max_height"] or math.inf) - calc["height"]
                add_height = min(add_height, max_add)
                calc["height"] += add_height
                remaining_height -= add_height
                remaining_height_expansion -= h_exp

            # Put everything back in order
            row_calcs.sort(key=lambda c: c["row"])

        y = area.position.y

        for calc in row_calcs:
            calc["y"] = y
            y += calc["height"]

        child_areas: RectangleList = list()

        for row in range(self.widget_rows):
            for column in range(self.widget_columns):
                column_calc = column_calcs[column]
                row_calc = row_calcs[row]
                child_areas.append(Rectangle(x=column_calc["x"],
                                             y=row_calc["y"],
                                             w=column_calc["width"],
                                             h=row_calc["height"]))

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
