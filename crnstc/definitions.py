import pathlib

ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent
ASSETS_PATH = ROOT_PATH / "assets"
SHADERS_PATH = ASSETS_PATH / "shaders"
TEXTURES_PATH = ASSETS_PATH / "textures"

# FPS_CAP = None
FPS_CAP = 60

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

CHUNK_SIZE = 16
CHUNK_SHAPE = (CHUNK_SIZE, CHUNK_SIZE, CHUNK_SIZE)

TERRAIN_HEIGHT_MULTIPLIER = 10
TERRAIN_STRETCH = 10
