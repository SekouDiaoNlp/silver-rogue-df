import random

import pygame, sys
from pygame.locals import *
from autoclass import autoclass

import spritesheets
import generate

pygame.init()

IS_FULLSCREEN = False

# Declare player and entities as global variables
player = None
entities = None


TILE_W = 12 # Tile size, in pixels
TILE_H = 12
CHAR_W = 18 # Screen size, in tiles
CHAR_H = 18    

# Screen size, in pixels
SCREEN_W = TILE_W * CHAR_W
SCREEN_H = TILE_H * CHAR_H

# If the player should move when an arrow key is held
MOVE_WHEN_HELD = True

# Default map width and height for a local map
mapw = 64
maph = 64

# Player position in local map
playerx = 10
playery = 10
playerz = 10

# Player position in the world
playerworldx = 2
playerworldy = 2

# Camera position
camerax = 0
cameraz = 0

# Size in local maps of the whole world
# (the world is supposed to be round, not yet implemented)
worldw = 48
worldh = 48

# this is a 2-dimensional array for the z-index of things:
# i.e., the player has to be drawn above grass
zindex_buf = [[-100 for _ in range(maph)] for _ in range(mapw)]
# I made a way to add foreground and background colors to entitities easily
# i'll call it "Color notation" here
# It works as follows:
#   - A colored tile is represented by a string
#   - The string has the format [foreground[:background]:]character
#   - If the character starts with whitespace, then interpret the rest of string as an hexadecimal representation of the character
#   - Examples:
#       - R:@ = Red "@"
#       - B:G:w = Blue "w" with a green background
#       - Y: 2741 = a yellow Unicode 0x2741: Flower emoji

COLOR_MAP = {
    "0": (0,0,0),
    "R": (255,0,0),
    "G": (0,255,0),
    "Y": (255,255,0),
    "B": (0,0,255),
    "M": (255,0,255),
    "C": (0,255,255),
    "W": (255,255,255)
}

# Class for the map, works like a set/dict and iterator
class Map:
    def __init__(self, entity_list):
        self.d = {}
        for i in entity_list:
            self.d[i.x,i.y,i.z] = i
    def add(self, *items):
        for i in items:
            self.d[i.x,i.y,i.z] = i
    def __contains__(self,*items):
        for i in items:
            if type(i) == tuple:
                if len(i) == 3:
                    return self.d.has_key(i.x,i.y,i.z)
            else:
                return self.d[i.x,i.y,i.z] == i
    has = __contains__
    def __getitem__(self,item):
        if type(item) == tuple:
            if len(item) == 3:
                return self.d.get((item[0],item[1],item[2]))

    def remove(self,*items):
        for i in items:
            del self.d[i.x,i.y,i.z]

    def __iter__(self):
        self.i = iter(self.d.values())
        return self.i
    def __next__(self):
        return self.i.__next__()
screen = None
def update_mode():
    global screen
    flags = RESIZABLE
    flags |= pygame.FULLSCREEN if IS_FULLSCREEN else 0
    screen = pygame.display.set_mode((SCREEN_H, SCREEN_W), flags) # Create the screen

update_mode()

sheet = spritesheets.spritesheet('tileset.png') # Load the sheet
backdrop = pygame.Rect(0, 0, SCREEN_W, SCREEN_H)

# Gets the surface in the tileset for a specific character
def get_surf(pos, fgcol = 'W', bgcol = '0'):
    if type(pos) == str:
        pos = ord(pos)
    fgcol = COLOR_MAP[fgcol]
    bgcol = COLOR_MAP[bgcol]
    upper = (pos & 0xF0) / 16 # Upper bits determine row
    lower = pos & 0x0F # Lower bits determine column
    surf = sheet.image_at(((TILE_H * lower), (TILE_W * upper), TILE_W, TILE_H))
    arr = pygame.PixelArray(surf)
    arr.replace((255,0,255), bgcol)
    arr.replace((255,255,255), fgcol)
    del arr
    return surf

# Prints a character at a tile
def blit_char_at(char, tx, ty, fgcol = 'W', bgcol = '0'):
    global screen
    rect = pygame.Rect(tx * TILE_W, ty * TILE_H, TILE_W, TILE_H)
    screen.blit(get_surf(char,fgcol,bgcol), rect)

# Calls blit_char_at, but uses color notation
def char_notation_blit(col, tx, ty):
    global screen
    if type(col) == int:
        blit_char_at(col,tx,ty)
        return True

    k = col.split(':')
    if k[-1][0] == ' ' and len(k[-1]) > 1:
        k[-1] = chr(int(k[-1][1:], 16)) # Convert to base-16 int, then get the corresponding character
    if len(k) == 1:
        blit_char_at(col,tx,ty)
    elif len(k) == 2:
        blit_char_at(k[1],tx,ty,k[0])
    elif len(k) == 3:
        blit_char_at(k[2],tx,ty,k[0], k[1])
    return True

@autoclass
class Entity:
    def __init__(self, char = ' ', x = 0, y = 0, z = 0, passable = False, draw_index = 0, slope = 0, attrs = set()):
        pass
    def print(self):
        #log(self.x,self.y,self.z)
        global zindex_buf
        if CHAR_H <= self.z + cameraz:
            return
        elif CHAR_W <= self.x + camerax:
            return
        if self.draw_index < zindex_buf[self.x][self.z]:
            return
        zindex_buf[self.x][self.z] = self.draw_index
        char_notation_blit(self.char, self.x + camerax, self.z + cameraz)


# Makes a grass entity
def Grass(x,y,z):
    ch = random.choice([',','\'','"'])
    ch = 'G:0:' + ch
    e = Entity(ch, x, y, z, True, -1)
    e.attrs.add('terrain')
    return e

@autoclass
class WorldTile:
    def __init__(self, char = ' ', x = 0, z = 0, worldseed = random.random() * 10 ** 6, passable = False, draw_index = 1):
        pass
    def gen(self):
        global zindex_buf
        # Generate the local map
        map_gened = generate.terrain.main(self.worldseed, mapw, maph, self.x, self.z)
        zindex_buf = [[-100 for _ in range(maph)] for _ in range(mapw)]

        entities = []
        for i in range(0,mapw):
            for j in range(0,maph):
                # i // 8 is to make the world a slope (a smooth one)
                entities.append(Grass(i,int(map_gened[i][j] * 10 + 10),j))
        entities = Map(entities)

        new_entities = Map(entities.d.values())
        # Generate slopes in the terrain "cliffs"
        for i in filter(lambda x: 'terrain' in x.attrs, entities.d.values()):
            # Search for adjacent tiles in the higher layer
            for e in (entities[i.x + 1, i.y + 1, i.z],entities[i.x + 1, i.y + 1, i.z + 1],entities[i.x - 1, i.y + 1, i.z],entities[i.x, i.y + 1, i.z - 1]):
                if e != None: # there is nothing on the tile
                    if 'terrain' in e.attrs: # make sure the tile is not the player or smth


                        entities[i.x, i.y, i.z].char = "G: 1F" # Up arrow
                        entities[i.x, i.y, i.z].slope = 1

                        if entities[e.x, i.y + 1, e.z]:
                            entities[e.x, i.y + 1, e.z].slope = -1
                            entities[e.x, i.y + 1, e.z].char = "G: 1E"
            # do the same but for lower layers
            for e in (entities[i.x + 1, i.y - 1, i.z],entities[i.x + 1, i.y - 1, i.z + 1],entities[i.x - 1, i.y - 1, i.z],entities[i.x, i.y - 1, i.z - 1]):
                if e != None: 
                    if 'terrain' in e.attrs:

                        entities[i.x, i.y, i.z].char = "G: 1E" # Up arrow
                        entities[i.x, i.y, i.z].slope = -1
                        if entities[e.x, i.y - 1, e.z]:
                            entities[e.x, i.y - 1, e.z].slope = 1
                            entities[e.x, i.y - 1, e.z].char = "G: 1F"
                        else:
                            pass
        entities = new_entities
        return new_entities
    def print(self):
        global zindex_buf
        if CHAR_H <= self.z - cameraz:
            return
        elif CHAR_W <= self.x - camerax:
            return
        if self.draw_index < zindex_buf[self.x][self.z]:
            return
        zindex_buf[self.x][self.z] = self.draw_index  
        char_notation_blit(self.char, self.x, self.z)      



class World(Map):
    def __init__(self, entity_list, seed = 0):
        self.d = {}
        for i in entity_list:
            self.d[i.x,i.z] = i
        self.seed = seed
    def add(self, *items):
        for i in items:
            i.worldseed = self.seed
            self.d[i.x,i.z] = i
    def __contains__(self,*items):
        for i in items:
            if type(i) == tuple:
                if len(i) == 2:
                    return self.d.has_key(i.x,i.z)
            else:
                return self.d[i.x,i.z] == i
    has = __contains__
    def __getitem__(self,item):
        if type(item) == tuple:
            if len(item) == 2:
                return self.d.get((item[0],item[1]))

    def remove(self,*items):
        for i in items:
            del self.d[i.x,i.z]

# Create world tile and entities
world = World([],seed = 0)

for i in range(0,worldw):
    for j in range(0,worldh):
        world.add(WorldTile('G:n',i,j))

def regenerate_world_tile(playerx = 4, playerz = 4):
    global player
    global entities
    worldtile = world[playerworldx,playerworldy]
    entities = worldtile.gen()
    player = Entity('@', playerx, 0, playerz, attrs = {'player'})
    for i in filter(lambda e: e.x == player.x and e.z == player.z, entities):
        player.y = i.y
    entities.add(player)

regenerate_world_tile()
# Variables for the loop
pygame.display.flip()
clock = pygame.time.Clock()

# Player state variables
is_on_worldmap = False

tick = True

# These two are to avoid having to redraw the screen every tick the screen is being resized
videoResizeWasHappening = False
timeSinceVideoResize = 0
# Direction in a keypad 
# 7 8 9
# 4 5 6 # 5 means the player is standing still
# 1 2 3
direction = 5

################ MAIN LOOP ####################################
while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == VIDEORESIZE:
            SCREEN_H = event.h
            SCREEN_W = event.w
            CHAR_H = int(SCREEN_H / TILE_H)
            CHAR_W = int(SCREEN_W / TILE_W)
            videoResizeWasHappening = True
            timeSinceVideoResize = 0
            zindex_buf = [[-100 for _ in range(maph)] for _ in range(mapw)]
            update_mode()
            for i in entities:
                if player.y == i.y:
                    i.print() 
        elif event.type == KEYDOWN:
            if event.key == K_UP:
                direction = 8
            elif event.key == K_DOWN:
                direction = 2
            elif event.key == K_LEFT:
                direction = 4
            elif event.key == K_RIGHT:
                direction = 6
            tick = True
        elif event.type == KEYUP:
            mods = pygame.key.get_mods()
            if event.key in (K_UP, K_DOWN, K_LEFT, K_RIGHT):
                direction = 5
            if mods & KMOD_SHIFT:
                if event.key == K_m:
                    # Map or travel
                    is_on_worldmap = not is_on_worldmap
                if event.key == K_q:
                    print(player)

            if event.key == K_F11:
                IS_FULLSCREEN = not IS_FULLSCREEN
                update_mode()
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
    timeSinceVideoResize += 1
    if direction != 5 and MOVE_WHEN_HELD:
        tick = True
    if timeSinceVideoResize > 10 and videoResizeWasHappening:
        tick = True
        videoResizeWasHappening = False
    if not is_on_worldmap: # Local view
        if tick:
            tile_at_player = entities[player.x, player.y, player.z]
            if tile_at_player == None:
                print('You somehow got out of the map. You crashed the program')

            def move_player_according_to_direction():
                global playerworldx
                global playerworldy
                global player
                if direction == 2:
                    player.z += 1
                if direction == 4:
                    player.x -= 1
                    
                if direction == 6:
                    player.x += 1
                    
                if direction == 8:
                    player.z -= 1

                if direction != 5:
                    player.y += tile_at_player.slope
                if player.x < 0:
                    playerworldx -= 1
                    player.x = mapw - 1
                    regenerate_world_tile(player.x, player.z)
                if player.z < 0:
                    playerworldy -= 1
                    player.z = maph - 1
                    regenerate_world_tile(player.x, player.z)
                if player.x >= mapw:
                    playerworldx += 1
                    player.x = 0
                    regenerate_world_tile(player.x, player.z)
                if player.z >= maph:
                    playerworldy += 1
                    player.z = 0
                    regenerate_world_tile(player.x, player.z)

                # Trick to undo player Y movement if player stepped from a slope in the reverse direction
                if entities[player.x, player.y, player.z] == None:
                    if tile_at_player.slope != 0:
                        player.y -= tile_at_player.slope
                    return
                        
                # Trick to undo player Y movement if the player is walking parallel to the slope
                if entities[player.x, player.y, player.z].slope == tile_at_player.slope:
                    if direction != 5:
                        player.y -= tile_at_player.slope
            move_player_according_to_direction()

        if tick: # Graphics tick, redrawing and stuff. Split it from the main tick when the game gets too large

            # Move camera
            camerax -= player.x - tile_at_player.x
            cameraz -= player.z - tile_at_player.z
            zindex_buf = [[-100 for _ in range(maph)] for _ in range(mapw)]
            screen.fill((0,0,0)) # TODO only redraw everything if the camera has moved
            for i in entities:
                
                if player.y == i.y:
                    i.print() 
                
            pygame.display.update()

        if tick:
            last_player_pos = tile_at_player.x, tile_at_player.y, tile_at_player.z
    else:
        if tick:
            for i in world:
                i.print()
            pygame.display.update()

    tick = False
    clock.tick(30)