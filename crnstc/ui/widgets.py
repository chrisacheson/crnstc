from typing import List, Optional, Tuple, Type
from dataclasses import dataclass, field
import random

from tcod.console import Console
import tcod.image

from crnstc.color import Color
from crnstc.geometry import Rectangle, Vector
from crnstc.ui.layouts import Layout


Float2Tuple = Tuple[float, float]
WidgetList = List["Widget"]
LayoutClass = Type[Layout]
OptLayoutClass = Optional[LayoutClass]
RectangleList = List[Rectangle]
OptColor = Optional[Color]
OptStr = Optional[str]


@dataclass
class Widget:
    children: WidgetList = field(default_factory=list)
    layout: OptLayoutClass = None
    min_size: Vector = Vector(0, 0)
    max_size: Vector = Vector(0, 0)
    expansion: Float2Tuple = (1.0, 1.0)

    def __post_init__(self) -> None:
        # The area that the last call to render() requested we use for
        # rendering
        self.requested_area: Rectangle = Rectangle(0, 0, 0, 0)
        # The area that we actually used on the last call to render()
        self.actual_area: Rectangle = Rectangle(0, 0, 0, 0)

    @property
    def aggregate_min_size(self) -> Vector:
        if self.layout:
            return self.layout.aggregate_min_size(self)
        else:
            return self.min_size

    @property
    def aggregate_max_size(self) -> Vector:
        if self.layout:
            return self.layout.aggregate_max_size(self)
        else:
            return self.max_size

    def render(self, surface: Console, area: Rectangle) -> None:
        child_areas: RectangleList

        if area != self.requested_area:
            # Area changed, recompute layout
            self.requested_area = area

            if self.layout:
                min_size = self.layout.aggregate_min_size(self)
            else:
                min_size = self.min_size

            # Enforce min_size
            self.actual_area = Rectangle(
                *area.position,
                w=max(area.w, min_size.dx),
                h=max(area.h, min_size.dy),
            )

            if self.layout:
                child_areas = self.layout.calculate_layout(
                    widget=self,
                    area=self.actual_area,
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

        """
        return

    def render_after_children(self, surface: Console,
                              area: Rectangle) -> None:
        """
        Virtual method called after this widget's child widgets are rendered.

        """
        return


@dataclass
class ColorBox(Widget):
    color: OptColor = None

    def render_before_children(self, surface: Console,
                               area: Rectangle) -> None:
        super().render_before_children(surface=surface, area=area)

        if not self.color:
            self.color = Color(r=random.randint(0x00, 0xFF),
                               g=random.randint(0x00, 0xFF),
                               b=random.randint(0x00, 0xFF))

        surface.draw_rect(*area, ch=ord(" "), bg=self.color)


@dataclass
class ImageBox(Widget):
    filename: OptStr = None

    def __post_init__(self):
        super().__post_init__()
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
