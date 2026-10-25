import math
from helpers.config import *

class Camera():
    def __init__(self):
        self.scroll = [0, 0]
        self.world_scroll = [0, 0]
        pass

    def follow(self, entity):
        self.scroll[0] -= (entity.render_pos[0] + self.scroll[0] - (1200 / 2)) / 10
        self.scroll[1] -= (entity.render_pos[1] + self.scroll[1] - (720 / 2)) / 10

        

    def Offset(self, scale):
        x = (screen_width - scale[0]) / 2
        y = (screen_height - scale[1]) / 2
        return [x, y]