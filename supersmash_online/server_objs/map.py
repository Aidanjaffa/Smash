import pygame
class Map():
    def __init__(self):
         self.map = self.txtLoadMap("assets/map1.txt")
         self.rects = self.get_rects()
    
    def txtLoadMap(self, name):
            with open(name, "r") as m:
                map = []
                data = m.read()
                m.close()
                data = data.split("\n")
                for row in data:
                    map.append(list(row))
                return map

    def get_rects(self):
        rects = []
        y = 0
        for row in self.map:
            x = 0
            for block in row:
                if block == "1":
                    rects.append(pygame.Rect(x * 40, y * 40, 40, 40))
                x += 1
            y += 1
        return rects