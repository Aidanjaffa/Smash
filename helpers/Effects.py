import pygame, random

pygame.init()
#screen_width, screen_height = 800, 600
#screen = pygame.display.set_mode((screen_width, screen_height))
#pygame.display.update()

#clock = pygame.time.Clock()

Exit = False


class Effects(object):
    def __init__(self):
        self.particles = []
        self.waves = []
        pass

    def Draw_Particles(self, X, Y, height, Colour, decay, surf, scroll=[0, 0]):
        self.particles.append([[X + scroll[0], Y + scroll[1]], [random.randint(0, 20) / 10 - 1, height], random.randint(4, 7)])

        point = 0
        for particle in self.particles:
            pygame.draw.circle(surf, Colour, (int(particle[0][0]), int(particle[0][1])), int(particle[2]))
            # pygame.draw.circle()
            particle[0][1] += particle[1][1]
            particle[0][0] += particle[1][0]
            particle[2] -= decay
            if particle[2] <= 0:
                del self.particles[point]

            point += 1

        pass

    def drawShockwave(self, surf):
        for wave in self.waves: #                       position          radius     width of border
            pygame.draw.circle(surf, (255, 255, 255), (wave[0], wave[1]), wave[2], int(wave[3]))
            wave[2] += random.randint(3, 5)
            wave[3] -= 0.7
            if wave[3] <= 1:
                self.waves.remove(wave)

    def addShockwave(self, x, y, size, decay):
        self.waves.append([x, y, size, decay])


Effect = Effects()
# while not Exit:
#     screen.fill((50, 50, 50))
#     #Effect.Draw_Particles(300, 500, -3, (255, 255, 255), 0.1)
#     Effect.drawShockwave()
#
#     for event in pygame.event.get():
#         if event.type == pygame.QUIT:
#             Exit = True
#
#     pygame.display.update()
#     clock.tick(60)


