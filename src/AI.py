'''
Created on 10.3.2013

@author: Alex
'''
import libtcodpy as libtcod
from Message import *

class NPC:
    def __init__(self, player):
        self.player = player
        
    def take_turn(self, game_msgs):
        npc = self.owner
        if self.owner.x <= 4:
            self.owner.move(1, 0)
        if self.owner.x >= 79:
            self.owner.move(-1, 0)
        if self.owner.y <= 4:
            self.owner.move(0, 1)
        if self.owner.y >= 79:
            self.owner.move(0, -1)
        if self.owner.x > 4 and self.owner.x < 79 and self.owner.y > 4 and self.owner.y < 39: #I hate magic numbers, but for now they'll do
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
    
class questgiver:
    def __init__(self, player):
        self.player = player
    def take_turn(self, game_msgs):
        pass
            
class BasicMonster:
    #AI for a basic monster.
    def __init__(self, player):
        self.player = player
        
    def take_turn(self, game_msgs):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        #if libtcod.map_is_in_fov(self.fov_map, monster.x, monster.y):
 
        #move towards player if far away
        if monster.distance_to(self.player) >= 2 and monster.distance_to(self.player) < 7:
            monster.move_towards(self.player.x, self.player.y)
            
        elif monster.distance_to(self.player) >= 7:
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))

        #close enough, attack! (if the player is still alive.)
        elif self.player.fighter.hp > 0:
            monster.fighter.attack(self.player, game_msgs, self.player)
 
class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, game_msgs, num_turns=5):
        self.old_ai = old_ai
        self.num_turns = num_turns
        self.game_msgs = game_msgs
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
 
        else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red, game_msgs)