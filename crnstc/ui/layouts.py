from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Tuple, TYPE_CHECKING

from crnstc.geometry import (Line1d, Line1dList, Rectangle, StretchyArea,
                             StretchyLength, StretchyLengthIterable)

if TYPE_CHECKING:
    from crnstc.ui.widgets import Widget

    Int2Tuple = Tuple[int, int]
    RectangleList = List[Rectangle]
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


class HorizontalLayout(Layout):
    """
    Places child widgets side by side in the attached widget's rendering area.

    """
    @property
    def aggregate_size(self) -> StretchyArea:
        stretchy_width = StretchyLength.sum(
            child.aggregate_size.stretchy_width
            for child in self.widget.children
        )
        stretchy_height = StretchyLength.most_restrictive(
            child.aggregate_size.stretchy_height
            for child in self.widget.children
        )
        agg_size = StretchyArea(*stretchy_width, *stretchy_height)
        return StretchyArea.most_restrictive((agg_size, self.widget.size),
                                             *self.widget.size.expansion)

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        stretchy_lengths: StretchyLengthIterable = (
            child.aggregate_size.stretchy_lengths[0]
            for child in self.widget.children
        )
        return Rectangle.multiple_from_lines(
            horizontal=area.horizontal_line.allocate(stretchy_lengths),
            vertical=(area.vertical_line,),
        )


class VerticalLayout(Layout):
    """
    Stacks child widgets vertically in the attached widget's rendering area.

    """
    @property
    def aggregate_size(self) -> StretchyArea:
        stretchy_width = StretchyLength.most_restrictive(
            child.aggregate_size.stretchy_width
            for child in self.widget.children
        )
        stretchy_height = StretchyLength.sum(
            child.aggregate_size.stretchy_height
            for child in self.widget.children
        )
        agg_size = StretchyArea(*stretchy_width, *stretchy_height)
        return StretchyArea.most_restrictive((agg_size, self.widget.size),
                                             *self.widget.size.expansion)

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        stretchy_lengths: StretchyLengthIterable = (
            child.aggregate_size.stretchy_lengths[1]
            for child in self.widget.children
        )
        return Rectangle.multiple_from_lines(
            horizontal=(area.horizontal_line,),
            vertical=area.vertical_line.allocate(stretchy_lengths),
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
        stretchy_width = StretchyLength.sum(
            self._column_stretchy_width(column)
            for column in range(self.widget_columns)
        )
        stretchy_height = StretchyLength.sum(
            self._row_stretchy_height(row)
            for row in range(self.widget_rows)
        )
        agg_size = StretchyArea(*stretchy_width, *stretchy_height)
        return StretchyArea.most_restrictive((agg_size, self.widget.size),
                                             *self.widget.size.expansion)

    def _column_stretchy_width(self, column: int) -> StretchyLength:
        stretchy_widths = [child.aggregate_size.stretchy_lengths[0]
                           for child
                           in self.get_children_in_column(column)]
        expansion: float = sum([s.expansion for s in stretchy_widths])
        return StretchyLength.most_restrictive(stretchy_widths, expansion)

    def _row_stretchy_height(self, row: int) -> StretchyLength:
        stretchy_heights = [child.aggregate_size.stretchy_lengths[1]
                            for child
                            in self.get_children_in_row(row)]
        expansion: float = sum([s.expansion for s in stretchy_heights])
        return StretchyLength.most_restrictive(stretchy_heights, expansion)

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        hlines: Line1dList = area.horizontal_line.allocate(
            self._column_stretchy_width(column)
            for column in range(self.widget_columns)
        )
        vlines: Line1dList = area.vertical_line.allocate(
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


class PaddingLayout(Layout):
    """
    Place a single child widget within the attached widget's rendering area at
    a location determined by the specified padding values.

    """
    def __init__(self, all_sides: StretchyLength = StretchyLength(),
                 left: StretchyLength = None,
                 right: StretchyLength = None,
                 top: StretchyLength = None,
                 bottom: StretchyLength = None):
        """
        Args:
            all_sides: Padding to apply to any unspecified side.
            left: Padding to the left of the child widget.
            right: Padding to the right of the child widget.
            top: Padding above the child widget.
            bottom: Padding below the child widget.

        """
        super().__init__()
        self.left = left or all_sides
        self.right = right or all_sides
        self.top = top or all_sides
        self.bottom = bottom or all_sides

    @property
    def aggregate_size(self) -> StretchyArea:
        child = self.widget.children[0]
        stretchy_width = StretchyLength.sum((self.left,
                                             child.size.stretchy_width,
                                             self.right))
        stretchy_height = StretchyLength.sum((self.top,
                                              child.size.stretchy_height,
                                              self.bottom))
        agg_size = StretchyArea(*stretchy_width, *stretchy_height)
        return StretchyArea.most_restrictive((agg_size, self.widget.size),
                                             *self.widget.size.expansion)

    def calculate_layout(self, area: Rectangle) -> RectangleList:
        child = self.widget.children[0]
        horizontal: Line1d = area.horizontal_line.allocate(
            (self.left, child.size.stretchy_width, self.right)
        )[1]
        vertical: Line1d = area.vertical_line.allocate(
            (self.top, child.size.stretchy_height, self.bottom)
        )[1]
        return [Rectangle.from_lines(horizontal=horizontal, vertical=vertical)]
