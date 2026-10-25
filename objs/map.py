import pygame
from PIL import Image

class map:
    def __init__(self):
        self.map = self.load_map("assets/map1.png")
        # dictionary of the tile sprites
        self.sprites = {"grass": pygame.image.load("assets/grass.png"),
                        "dirt": pygame.image.load("assets/dirt1.png"),
                        "concrete": pygame.transform.scale(pygame.image.load("assets/dirt.png"), (40, 40)),
                        "sky grass": pygame.image.load("assets/Lv3_Grass.png"),
                        "sky dirt": pygame.image.load("assets/Lv3_Block.png")}
        # all the tiles from the 2d array get put into a 1d array so i dont need 2 for loops for iteration
        # also are turned into pygame.rect objects for ease of collision checking
        self.rects = []
        pass

    def Draw(self, surf, scroll):
        # rects is reset every time other wise it gets very laggy
        self.rects = []
        # x and y are set to -1 so we get 1 column of blocks outside the screen so when the screenshakes it doesnt look
        # weird

        # then this iterates through the 2d array that was returned from load_map() for each line and tile
        # each iteration of the for loop is incrementing its own axis by 1. the axis is multiplied by the size i
        # want the blocks to be. it checks if that item corrosponds and draws the tile where needed.
        y = -1
        for line in self.map:
            x = -1
            for block in line:
                if block == (91, 91, 91):
                    surf.blit(self.sprites["concrete"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))
                if block == (35, 169, 48):
                    surf.blit(self.sprites["grass"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))
                if block == (169, 102, 35):
                    surf.blit(self.sprites["dirt"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))
                if block == (31, 79, 114):
                    surf.blit(self.sprites["sky grass"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))
                if block == (60, 92, 115):
                    surf.blit(self.sprites["sky dirt"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))
                    
                if block == "1":
                    surf.blit(self.sprites["concrete"], (x * 40 + scroll[0], y * 40 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 40 + scroll[0], y * 40 + scroll[1], 40, 40))

                x += 1
            y += 1
        pass

    def load_map(self, name):
        img = Image.open(name)
        width, height = img.size
        colors = []
        for y in range(height):
            row = []
            for x in range(width):
                tup = img.getpixel((x, y))
                tup = tup[:3]
                row.append(tup)
            colors.append(row)
        return colors

    def txtLoadMap(self, name):
        with open(name, "r") as m:
            map = []
            data = m.read()
            m.close()
            data = data.split("\n")
            for row in data:
                map.append(list(row))
            return map