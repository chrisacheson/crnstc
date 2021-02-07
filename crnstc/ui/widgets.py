import random
from typing import List, Optional, Tuple

from tcod.console import Console
import tcod.image

from crnstc.color import Color
from crnstc.geometry import Rectangle, StretchyArea
from crnstc.ui.layouts import Layout


Float2Tuple = Tuple[float, float]
OptLayout = Optional[Layout]
OptColor = Optional[Color]
OptStr = Optional[str]
RectangleList = List[Rectangle]
WidgetList = List["Widget"]


class Widget:
    """
    Basic user interface building block. This is the base class that other
    widgets inherit from, but by itself it only acts as a placeholder or a
    container for child widgets. Subclasses can override the
    render_before_children() and render_after_children() methods in order to
    draw on the screen.

    """
    def __init__(self, children: WidgetList = None, layout: OptLayout = None,
                 size: StretchyArea = None):
        """
        Args:
            children: Optional list of widgets to be used as the children of
                this widget.
            layout: Optional Layout object for determining placement of child
                widgets within this widget's rendering area. If unspecified,
                child widgets will not be rendered.
            size: Optional StretchyArea object describing how this widget
                should be sized. If unspecified, the widget will have no
                minimum or maximum size, and will have horizontal and vertical
                expansion weights of 1.0.

        """
        self.children = children or list()
        self.layout = layout
        self.size: StretchyArea = size or StretchyArea()

        # The area that the last call to render() requested we use for
        # rendering
        self.requested_area: Rectangle = Rectangle(0, 0, 0, 0)
        # The area that we actually used on the last call to render()
        self.actual_area: Rectangle = Rectangle(0, 0, 0, 0)

    @property
    def layout(self) -> OptLayout:
        """The widget's Layout object."""
        return self._layout

    @layout.setter
    def layout(self, value: OptLayout):
        self._layout = value

        if self._layout:
            self._layout.widget = self

    @property
    def aggregate_size(self) -> StretchyArea:
        """The size parameters of this widget and its children."""
        if self.layout:
            return self.layout.aggregate_size
        else:
            return self.size

    def render(self, surface: Console, area: Rectangle) -> None:
        """
        Draw the widget. Subclasses should override render_before_children() or
        render_after_children() instead of this method.

        Args:
            surface: The console to draw on.
            area: The area of the console that the widget should be drawn into.
                If this is smaller than the widget's aggregate minimum size,
                the widget will overflow the boundary.

        """
        child_areas: RectangleList

        if area != self.requested_area:
            # Area changed, recompute layout
            self.requested_area = area

            min_size = self.aggregate_size.min_size

            # Enforce min_size
            self.actual_area = Rectangle(
                *area.position,
                w=max(area.w, min_size.dx),
                h=max(area.h, min_size.dy),
            )

            if self.layout:
                child_areas = self.layout.calculate_layout(
                    area=self.actual_area
                )
        else:
            child_areas = [child.requested_area for child in self.children]

        self.render_before_children(surface=surface, area=self.actual_area)

        if self.layout:
            for child, child_area in zip(self.children, child_areas):
                child.render(surface=surface, area=child_area)

        self.render_after_children(surface=surface, area=self.actual_area)

    def render_before_children(self, surface: Console,
                               area: Rectangle) -> None:
        """
        Virtual method called before this widget's child widgets are rendered.

        Args:
            surface: The console to draw on.
            area: The area of the console that the widget should be drawn into.
                This will be at least as large as the widget's aggregate
                minimum size, though it may be larger than the aggregate
                maximum.

        """
        return

    def render_after_children(self, surface: Console,
                              area: Rectangle) -> None:
        """
        Virtual method called after this widget's child widgets are rendered.

        Args:
            surface: The console to draw on.
            area: The area of the console that the widget should be drawn into.
                This will be at least as large as the widget's aggregate
                minimum size, though it may be larger than the aggregate
                maximum.

        """
        return


class ColorBox(Widget):
    """
    A simple colored box. Useful for testing layouts.

    """
    def __init__(self, children: WidgetList = None, layout: OptLayout = None,
                 size: StretchyArea = None, color: OptColor = None):
        """
        Args:
            children: Optional list of widgets to be used as the children of
                this widget.
            layout: Optional Layout object for determining placement of child
                widgets within this widget's rendering area. If unspecified,
                child widgets will not be rendered.
            size: Optional StretchyArea object describing how this widget
                should be sized. If unspecified, the widget will have no
                minimum or maximum size, and will have horizontal and vertical
                expansion weights of 1.0.
            color: Optional color for this widget. Defaults to a random color.

        """
        super().__init__(children, layout, size)
        self.color = color

    def render_before_children(self, surface: Console,
                               area: Rectangle) -> None:
        super().render_before_children(surface=surface, area=area)

        if not self.color:
            self.color = Color(r=random.randint(0x00, 0xFF),
                               g=random.randint(0x00, 0xFF),
                               b=random.randint(0x00, 0xFF))

        surface.draw_rect(*area, ch=ord(" "), bg=self.color)


class ImageBox(Widget):
    """
    A widget that displays a semigraphics image.

    """
    def __init__(self, children: WidgetList = None, layout: OptLayout = None,
                 size: StretchyArea = None, filename: OptStr = None):
        """
        Args:
            children: Optional list of widgets to be used as the children of
                this widget.
            layout: Optional Layout object for determining placement of child
                widgets within this widget's rendering area. If unspecified,
                child widgets will not be rendered.
            size: Optional StretchyArea object describing how this widget
                should be sized. If unspecified, the widget will have no
                minimum or maximum size, and will have horizontal and vertical
                expansion weights of 1.0.
            filename: Optional image file path. Defaults to None.

        """
        super().__init__(children, layout, size)
        self.filename = filename
        self._filename: OptStr = None

    def render_before_children(self, surface: Console,
                               area: Rectangle) -> None:
        super().render_before_children(surface=surface, area=area)

        if not self.filename:
            return

        if self.filename != self._filename:
            # New filename, need to load a new image
            self._filename = self.filename
            # Image with alpha channel removed
            image = tcod.image.load(self.filename)[:, :, :3]
            # Use an intermediate console to make sure that the image doesn't
            # overflow our rendering area. The width and height of the image
            # will be halved when drawn by draw_semigraphics().
            self._image_console = Console(width=image.shape[1] // 2,
                                          height=image.shape[0] // 2,
                                          order="F")
            self._image_console.draw_semigraphics(image, x=0, y=0)

        self._image_console.blit(surface, *area.position, 0, 0,
                                 *area.dimensions)