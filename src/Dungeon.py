'''
Created on 10.3.2013

@author: Alex
'''
import libtcodpy as libtcod
from Tile import *

class Dungeon:
    def __init__(self, h, w):
        self.dungeon = [[ Tile(True)
        for y in range(h) ]
            for x in range(w) ]
    
    def is_blocked(self, x, y, objects):
    #first test the map tile
        if self.dungeon[x][y].blocked:
            return True
     
        #now check for any blocking objects
        for object in objects:
            if object.blocks and object.x == x and object.y == y:
                return True
     
        return False
 
    def create_room(self, room):
        #go through the tiles in the rectangle and make them passable
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.dungeon[x][y].blocked = False
                self.dungeon[x][y].block_sight = False
     
    def create_h_tunnel(self, x1, x2, y):
        #horizontal tunnel. min() and max() are used in case x1>x2
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.dungeon[x][y].blocked = False
            self.dungeon[x][y].block_sight = False
     
    def create_v_tunnel(self, y1, y2, x):
        #vertical tunnel
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.dungeon[x][y].blocked = False
            self.dungeon[x][y].block_sight = False
            
    def get_dungeon(self):
        return self.dungeon