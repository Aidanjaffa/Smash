import math
from helpers.config import *

class Camera():
    def __init__(self):
        self.scroll = [0, 0]
        pass

    def Scaling(self, playerDict):
        """so for the screen scaling i should calculate the distance between the furthest players, then i would get it so
        the screen is say 20 pixels away from the players edge, I would calculate the total length in size in pixels with
        screen padding and player distance. then i would want to find the factor between the x distance and the fixed
        screen size of 800 pixels and multiply everything by that factor that was calculated"""
        max = 1
        for key1, player1 in playerDict.items():
            if player1.lives > 0:
                for key2, player2 in playerDict.items():
                    if player2.lives > 0:
                        if key1 != key2:
                            distx = (player2.rect.x + self.scroll[0]) - (player1.rect.x + self.scroll[0])
                            disty = (player2.rect.y + self.scroll[1]) - (player1.rect.y + self.scroll[1])
                            distance = math.sqrt((distx ** 2) + (disty ** 2))
                            if distance > max:
                                max = distance

        factor = 0
        factorX = screen_width / (max + 150)
        factorY = screen_height / (max + 150)
        if factorX > factorY:
            factor = factorX
        else:
            factor = factorY
        # print(factor)
        return [factor * 1200, factor * 720]

    def Centroid(self, playerDict):
        # Finding the average of the each players X and Y
        Ox = 0
        Oy = 0
        count = 0
        for key in playerDict.keys():
            if playerDict[key].lives > 0: # Finding the centre between only alive players
                Ox += playerDict[key].pos[0]
                Oy += playerDict[key].pos[1]
                count += 1
        try: 
            Ox = Ox / count
            Oy = Oy / count
        except ZeroDivisionError:
            return [600, 500]
        else:
            return Ox + self.scroll[0], Oy + self.scroll[1]

    def Offset(self, scale):
        x = (screen_width - scale[0]) / 2
        y = (screen_height - scale[1]) / 2
        return [x, y]