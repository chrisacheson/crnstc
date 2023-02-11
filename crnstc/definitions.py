import pathlib

ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent
ASSETS_PATH = ROOT_PATH / "assets"
SHADERS_PATH = ASSETS_PATH / "shaders"
TEXTURES_PATH = ASSETS_PATH / "textures"

# FPS_CAP = None
FPS_CAP = 60

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
