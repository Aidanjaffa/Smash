import pygame
from pygame import *

class AudioManager():
    def __init__(self, file : str):
        self.audio = file
        pass

    
    def load(self, file):
        pygame.mixer.music.load(file)


    def play(self):
        pygame.mixer.music.play(-1)

    
    