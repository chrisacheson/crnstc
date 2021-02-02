import tcod

from crnstc.geometry import Rectangle, Vector
from crnstc.ui.layouts import HorizontalLayout, VerticalLayout
from crnstc.ui.widgets import Widget, ColorBox, ImageBox


class UserInterface:
    def run(self) -> None:
        width_pixels = 1280
        height_pixels = 800
        game_name = "Cyberpunk Roguelike (Name Subject to Change)"

        tileset = tcod.tileset.load_tilesheet(
            path="assets/16x16-sb-ascii.png",
            columns=16,
            rows=16,
            charmap=tcod.tileset.CHARMAP_CP437,
        )

        with tcod.context.new(
            width=width_pixels,
            height=height_pixels,
            tileset=tileset,
            title=game_name,
            renderer=tcod.context.RENDERER_OPENGL2,
        ) as context:
            console = context.new_console(order="F")

            # world_pane = ColorBox(min_size=Vector(80, 43))
            world_pane = ImageBox(
                filename="assets/beeple_mike_winkelman_dvde.png",
                min_size=Vector(80, 43),
            )
            status_pane = ColorBox()
            log_pane = ColorBox(expansion=(2.0, 1.0))
            info_section = Widget(children=[status_pane, log_pane],
                                  layout=HorizontalLayout)
            main_widget = Widget(children=[world_pane, info_section],
                                 layout=VerticalLayout)

            while True:
                # TODO: Render stuff
                console_shape = Rectangle(0, 0, console.width, console.height)
                main_widget.render(surface=console, area=console_shape)
                """
                for x in range(console.width):
                    for y in range(console.height):
                        blue = round(255.0 * x / console.width)
                        red = round(255.0 * y / console.width)
                        console.print(x, y, " ", bg=(red, 0, blue))
                console.print(0, 0, f"({console.width}, {console.height})")
                """
                context.present(console, integer_scaling=True)

                for event in tcod.event.wait():
                    context.convert_event(event)

                    if event.type == "QUIT":
                        raise SystemExit
                    elif event.type == "WINDOWRESIZED":
                        console = context.new_console(order="F")
