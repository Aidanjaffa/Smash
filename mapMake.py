import pygame
import math
from helpers.utils import load_text
from helpers.config import *

pygame.init()

width, height = 1200, 720
screen = pygame.display.set_mode((width, height))
mouse = [0, 0]
current = [0, 0]
initial = [0, 0]
offset = [0, 0]

scale = [480, 480]
cell_thickness = 40
grid_width = 22
grid_height = 22


background = pygame.transform.scale(pygame.image.load("assets/Lv1_BG1.png").convert_alpha(), (400 * 3, 300 * 3))

ground_tiles = {"concrete" : pygame.transform.scale(pygame.image.load("assets/dirt.png").convert_alpha(), (cell_thickness, cell_thickness))}
guy = pygame.transform.scale(pygame.image.load("assets/horatioStand.png"), (10 * 2, 16 * 2))


surf = pygame.Surface((cell_thickness * grid_width + 4, cell_thickness * grid_height + 4), pygame.SRCALPHA)

map = [[0 for x in range(grid_width)] for x in range(grid_height)]

def surf_offset(scale):
    x = (screen_width - scale[0]) / 2
    y = (screen_height - scale[1]) / 2
    return (x, y)


def draw_grid():
    for x in range(grid_width):
        pygame.draw.line(surf, Grey, (x * cell_thickness, 0), (x * cell_thickness, grid_width * cell_thickness), 4)
        for y in range(grid_height):
            rect = pygame.Rect(x * cell_thickness, y * cell_thickness, 40, 40)
            #pygame.draw.rect(surf, (25,25,25), rect)
            pygame.draw.line(surf, Grey , (0, y * cell_thickness), (grid_height * cell_thickness, y * cell_thickness), 4)
    
    pygame.draw.line(surf, Grey, ((grid_width * cell_thickness), 0), ((grid_width * cell_thickness), grid_height * cell_thickness), 4)
    pygame.draw.line(surf, Grey, (0, grid_height * cell_thickness), (grid_width * cell_thickness, grid_height * cell_thickness), 4)


def draw_block():
    y = 0
    for row in map:
        x = 0
        for block in row:
            if block == 1:
                surf.blit(ground_tiles["concrete"], (x * cell_thickness, y * cell_thickness))
            x += 1
        y += 1

def calc_index():
    canvas_x = (current[0] - camera_offset[0] - offset[0]) / (scale[0] / (grid_width * cell_thickness))
    canvas_y = (current[1] - camera_offset[1] - offset[1]) / (scale[1] / (grid_height * cell_thickness))

    x = int(canvas_x // cell_thickness)
    y = int(canvas_y // cell_thickness)
    return x, y


def save():
    with open("assets/new.txt", "w+") as f:
        for line in map:
            row = ""
            for b in line:
                row += str(b)
            row += "\n"
            f.write(row)
    

def load_map(name):
    with open(name, "r") as m:
        map = []
        data = m.read()
        m.close()
        data = data.split("\n")
        for row in data:
            map.append([int(c) for c in row])
        return map


pan = False
pencil = False
erase = False
left_click = False
show = True


run = True
while run:
    current = pygame.mouse.get_pos()

    camera_offset = surf_offset(scale)

    screen.fill((50,50,50))
    screen.blit(background, (0, -150))
    surf.fill((0,0,0,0))
    surf.blit(guy, (0, 410))

    load_text(str(current), White, (0, 0), pygame.font.Font("assets/joystix.otf", 12), screen)
    load_text(str(scale), White, (0, 15), pygame.font.Font("assets/joystix.otf", 12), screen)

    if pencil:
        load_text("Drawing Active", White, (300, 0), pygame.font.Font("assets/joystix.otf", 12), screen)
    if erase:
        load_text("Erasing Active", White, (300, 0), pygame.font.Font("assets/joystix.otf", 12), screen)
    if show:
        draw_grid()

    draw_block()

    new_surf = pygame.transform.scale(surf, tuple(scale))

    screen.blit(new_surf, (0 + camera_offset[0] + offset[0], 0 + camera_offset[1] + offset[1]))


    if left_click and pencil:
        
        x, y = calc_index()
        try:
            map[y][x] = 1
        except IndexError:
            pass
    
    elif left_click and erase:
        x, y = calc_index()
        try:
            map[y][x] = 0
        except IndexError:
            pass


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_EQUALS:
                scale[0] += 50
                scale[1] += 50
            if event.key == pygame.K_MINUS:
                scale[0] -= 50
                scale[1] -= 50

            if event.key == pygame.K_b:
                erase = False
                if pencil == False:
                    pencil = True
                elif pencil == True:
                    pencil = False

            if event.key == pygame.K_e:
                pencil = False
                if not erase:
                    erase = True
                elif erase:
                    erase = False
            
            if event.key == pygame.K_s:
                load_text("SAVING", White, (0, 15), pygame.font.Font("assets/joystix.otf", 12), screen)
                save()
            
            if event.key == pygame.K_m:
                if not show:
                    show = True
                elif show:
                    show = False
                
            if event.key == pygame.K_l:
                map = load_map("assets/new.txt")
                for row in map:
                    print(row)


        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                pan = True
                initial = list(pygame.mouse.get_pos())
            if event.button == 1:
                left_click = True

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                pan = False
            if event.button == 1:
                left_click = False
            
    if pan:
        diff = [(current[0] - initial[0]) / 20, (current[1] - initial[1]) / 20]
        offset[0] -= diff[0] / 2
        offset[1] -= diff[1] / 2

    pygame.display.update()
pygame.quit()
quit()


    
