from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, TYPE_CHECKING

from crnstc.geometry import (Line1dList, Rectangle, StretchyArea,
                             StretchyLength, StretchyLengthIterable, Vector)
from crnstc.utils import min_nonzero, sum_or_zero

if TYPE_CHECKING:
    from crnstc.ui.widgets import Widget

    DictList = List[dict]
    Int2Tuple = Tuple[int, int]
    IntList = List[int]
    OptWidget = Optional[Widget]
    RectangleList = List[Rectangle]
    StretchyAreaList = List[StretchyArea]
    VectorList = List[Vector]
    WidgetIterator = Iterator[Widget]


class Layout:
    """
    Base class inherited by other layout classes. A layout object is attached
    to a widget to determine the placement of its child widgets.

    """
    widget: Widget

    @property
    def aggregate_size(self) -> StretchyArea:
        """
        The minimum and maximum size of the widget and its children, along with
        the horizontal and vertical expansion weights of the widget itself.

        """
        raise NotImplementedError

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        """
        Calculate the placement of the widget's children based on the specified
        rendering area.

        Args:
            area: The widget's rendering area.

        Returns:
            A list of rendering areas corresponding to each child widget.

        """
        raise NotImplementedError


class SequentialLayout(Layout):
    """
    Base class for HorizontalLayout and VerticalLayout.

    """
    @property
    def aggregate_size(self) -> StretchyArea:
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

        sizes: StretchyAreaList = [child.aggregate_size
                                   for child in self.widget.children]

        agg_min: IntList = [0, 0]
        agg_min[span_dim] = sum(size.min_size[span_dim] for size in sizes)
        agg_min[other_dim] = max(size.min_size[other_dim] for size in sizes)

        agg_max: IntList = [0, 0]
        agg_max[span_dim] = sum_or_zero(size.max_size[span_dim]
                                        for size in sizes)
        agg_max[other_dim] = min_nonzero(size.max_size[span_dim]
                                         for size in sizes)

        wsize = self.widget.size
        # Check if the min size of the parent widget is larger than the min
        # size of its children
        agg_min[span_dim] = max(agg_min[span_dim], wsize.min_size[span_dim])
        agg_min[other_dim] = max(agg_min[other_dim], wsize.min_size[other_dim])

        # Check if the max size of the parent widget is smaller than the max
        # size of its children
        agg_max[span_dim] = min_nonzero((agg_max[span_dim],
                                         wsize.max_size[span_dim]))
        agg_max[other_dim] = min_nonzero((agg_max[other_dim],
                                          wsize.max_size[other_dim]))

        # Aggregate max size can't be smaller than aggregate min size
        for dim, value in enumerate(agg_max):
            if value:
                agg_max[dim] = max(value, agg_min[dim])

        return StretchyArea(min_size=Vector(*agg_min),
                            max_size=Vector(*agg_max),
                            expansion=self.widget.size.expansion)


class HorizontalLayout(SequentialLayout):
    """
    Places child widgets side by side in the attached widget's rendering area.

    """
    def calculate_layout(self, area: Rectangle) -> RectangleList:
        stretchy_lengths: StretchyLengthIterable = (
            child.aggregate_size.stretchy_lengths[0]
            for child in self.widget.children
        )
        return Rectangle.multiple_from_lines(
            horizontal=area.lines[0].allocate(stretchy_lengths),
            vertical=(area.lines[1],),
        )


class VerticalLayout(SequentialLayout):
    """
    Stacks child widgets vertically in the attached widget's rendering area.

    """
    def calculate_layout(self, area: Rectangle) -> RectangleList:
        stretchy_lengths: StretchyLengthIterable = (
            child.aggregate_size.stretchy_lengths[1]
            for child in self.widget.children
        )
        return Rectangle.multiple_from_lines(
            horizontal=(area.lines[0],),
            vertical=area.lines[1].allocate(stretchy_lengths),
        )


@dataclass
class GridLayout(Layout):
    """
    Arrange child widgets into a grid in the attached widget's rendering area.

    Args:
        widget_columns: How many columns of widgets the grid should have.
            Defaults to 2.
        widget_rows: How many rows of widgets the grid should have. Defaults to
            2.

    """
    widget_columns: int = 2
    widget_rows: int = 2

    @property
    def aggregate_size(self) -> StretchyArea:
        min_widths, max_widths = list(), list()
        min_heights, max_heights = list(), list()

        for column in range(self.widget_columns):
            min_width, max_width, _ = self._column_stretchy_width(column)
            min_widths.append(min_width)
            max_widths.append(max_width)

        for row in range(self.widget_rows):
            min_height, max_height, _ = self._row_stretchy_height(row)
            min_heights.append(min_height)
            max_heights.append(max_height)

        return StretchyArea(
            min_size=Vector(dx=sum(min_widths), dy=sum(min_heights)),
            max_size=Vector(dx=sum_or_zero(max_widths),
                            dy=sum_or_zero(max_heights)),
            expansion=self.widget.size.expansion,
        )

    def _column_stretchy_width(self, column: int) -> StretchyLength:
        stretchy_widths = [child.aggregate_size.stretchy_lengths[0]
                           for child
                           in self.get_children_in_column(column)]
        min_width: int = max([s.min_length for s in stretchy_widths])
        max_width: int = min_nonzero([s.max_length for s in stretchy_widths])
        expansion: float = sum([s.expansion for s in stretchy_widths])

        # Maximum can't be smaller than minimum
        if max_width:
            max_width = max(min_width, max_width)

        return StretchyLength(min_length=min_width, max_length=max_width,
                              expansion=expansion)

    def _row_stretchy_height(self, row: int) -> StretchyLength:
        stretchy_heights = [child.aggregate_size.stretchy_lengths[1]
                            for child
                            in self.get_children_in_row(row)]
        min_height: int = max([s.min_length for s in stretchy_heights])
        max_height: int = min_nonzero([s.max_length for s in stretchy_heights])
        expansion: float = sum([s.expansion for s in stretchy_heights])

        # Maximum can't be smaller than minimum
        if max_height:
            max_height = max(min_height, max_height)

        return StretchyLength(min_length=min_height, max_length=max_height,
                              expansion=expansion)

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        hlines: Line1dList = area.lines[0].allocate(
            self._column_stretchy_width(column)
            for column in range(self.widget_columns)
        )
        vlines: Line1dList = area.lines[1].allocate(
            self._row_stretchy_height(row)
            for row in range(self.widget_rows)
        )
        return Rectangle.multiple_from_lines(horizontal=hlines,
                                             vertical=vlines)

    def get_child_at_cell(self, column: int, row: int) -> Widget:
        index = self.get_index(column=column, row=row)
        return self.widget.children[index]

    def get_children_in_row(self, row: int) -> WidgetIterator:
        return (self.widget.children[i] for i in self.get_row_indexes(row=row))

    def get_children_in_column(self, column: int) -> WidgetIterator:
        return (self.widget.children[i]
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
