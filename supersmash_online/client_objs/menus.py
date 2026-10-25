import pygame
from helpers.utils import *
from helpers.config import *
from client_objs.Network import sio
import copy

global dt

arrow = pygame.transform.scale(pygame.image.load("assets/arrow.png").convert_alpha(), (8 * 5, 8 * 5))
arrow_left = pygame.transform.rotate(arrow, 90)
arrow_right = pygame.transform.rotate(arrow, -90)
arrow_down = pygame.transform.rotate(arrow, 180)

space_bar = pygame.transform.scale(pygame.image.load("assets/space.png").convert_alpha(), (24 * 5, 8 * 5))
ctrl = pygame.transform.scale(pygame.image.load("assets/Ctrl.png").convert_alpha(), (8 * 5, 8 * 5))


class MenuItem():
    def __init__(self, start_pos : list, text : str, text_pos, font):
        self.text = text
        self.text_pos = text_pos
        self.start_pos = start_pos

        self.font = font

        self.top_line = [(self.start_pos[0], self.start_pos[1]), (self.start_pos[0] + 300, self.start_pos[1])]
        self.bottom_line = [(self.start_pos[0], self.start_pos[1] + 35), (self.start_pos[0] + 290, self.start_pos[1] + 35)]
        self.connector = [(self.bottom_line[1][0], self.bottom_line[1][1]), (self.top_line[1][0], self.top_line[1][1])]
    
        self.rect = pygame.Rect(self.start_pos[0], self.start_pos[1], 300, 35)

        self.thickness = 3
        self.active = False

        self.SFX_volume = Slider((800, 300), 100)
        self.music_volume = Slider((800, 380), 120)
        
    
    def draw(self, surf):
        pygame.draw.line(surf, White, self.top_line[0], self.top_line[1], self.thickness)
        pygame.draw.line(surf, White, self.bottom_line[0], self.bottom_line[1], self.thickness)
        pygame.draw.line(surf, White, self.connector[0], self.connector[1], self.thickness)

        load_text(self.text, White, self.text_pos, self.font, surf)

        # pygame.draw.rect(surf, White, self.rect, 1)


    def update(self, surf, mouse_pos, mouse_rect):
        if self.active:
            if self.text == "Disconnect":
                sio.disconnect()
                pygame.quit()
            
            if self.text == "Options":
                load_text("SFX Volume", White, (500, 300), self.font, surf)
                self.SFX_volume.draw(surf)
                level = self.SFX_volume.move(mouse_pos, mouse_rect)

                load_text("Music Volume", White, (500, 380), self.font, surf)
                self.music_volume.draw(surf)
                level = self.music_volume.move(mouse_pos, mouse_rect)

                load_text("Toggle Fullscreen", White, (500, 460), self.font, surf)  
            
            if self.text == "Controls":
                surf.blit(arrow_left, (1000, 222))
                load_text("Move Left", White, (640, 230), self.font, surf)

                surf.blit(arrow_right, (1000, 292))
                load_text("Move Right", White, (640, 300), self.font, surf)

                surf.blit(space_bar, (1000, 362))
                load_text("Jump", White, (640, 370), self.font, surf)

                surf.blit(ctrl, (1000, 432))
                load_text("Dash", White, (640, 440), self.font, surf)

                surf.blit(arrow_down, (1000, 502)) 
                load_text("Down Attack", White, (640, 510), self.font, surf)



class Slider():
    def __init__(self, pos=[0, 0], current_position=0):
        self.pos = pos
        self.rect = pygame.Rect(self.pos[0] + current_position, self.pos[1], 23, 23)
        self.range = 200

        self.rail = pygame.Rect(self.pos[0], self.pos[1] + 5, self.range, 15)

    
    def draw(self, surf):
        pygame.draw.rect(surf, White, self.rect)
        pygame.draw.rect(surf, White, self.rail)


    def move(self, mouse_pos, rect):
        if self.rect.colliderect(rect):
            if pygame.mouse.get_pressed()[0]:
                if mouse_pos[0] < self.rail[0] + (self.rect[2] / 2):
                    self.rect[0] = self.rail[0]
                elif mouse_pos[0] > self.rail[0] + self.range - (self.rect[2] / 2):
                    self.rect[0] = self.rail[0] + 200 - 23
                else:
                    self.rect[0] = mouse_pos[0] - 10
        
        distance_along = self.rect[0] - self.rail[0]
        percent = (distance_along / self.range) * 113
        return int(percent)


menu_items = [MenuItem([0, 445], "Controls", (155, 450), pygame.font.Font("assets/joystix.otf", 19)), 
              MenuItem([0, 495], "Options", (170, 500), pygame.font.Font("assets/joystix.otf", 19)), 
              MenuItem([0, 545], "Disconnect", (130, 550), pygame.font.Font("assets/joystix.otf", 19))]


dt = 0
d = Dimmer()

def Pause(surf, fonts):
    global dt
    dt += 1
    
    d.dim()

    mouse = pygame.mouse.get_pos()
    mouse_rect = pygame.Rect(mouse[0], mouse[1], 10, 10)
    # pygame.draw.rect(surf, White, mouse_rect, 1)

    # print(mouse)
    
    load_text ("PAUSED", (255, 255, 255), (500, 100), fonts[1], surf)

    for item in menu_items:
        item.draw(surf)
        item.update(surf, mouse, mouse_rect)
        if mouse_rect.colliderect(item.rect):
            animate(item, 10)

            if pygame.mouse.get_pressed()[0]:
                match item.text:
                    case "Controls":
                        menu_items[0].active = True
                        menu_items[1].active = False
                        menu_items[2].active = False
                    case "Options":
                        menu_items[0].active = False
                        menu_items[1].active = True
                        menu_items[2].active = False
                    case "Disconnect":
                        menu_items[0].active = False
                        menu_items[1].active = False
                        menu_items[2].active = True
        else:
            animate(item, 3)



def animate(item, size):
    global dt
    if item.thickness != size: # if it hasnt reached its size

        if dt % 2 == 0:
            if size - item.thickness > 0: 
                item.thickness += 1
            
            elif size - item.thickness < 0: 
                item.thickness -= 1