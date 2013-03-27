'''
Created on 10.3.2013

@author: Alex
'''
import libtcodpy as libtcod
from Message import *

class Spell:
    def __init__(self, number, player, spell_function = None):
        self.number = number
        self.player = player
        self.spell_function = spell_function
       
    def cast_spell(self, game_msgs, player):
        if self.spell_function == 'heal':
            self.cast_heal(game_msgs, player)
            self.number-= 1
            return self.number
        else:
            print 'You dumb shit'
        """elif self.spell_function == 'fireball':
            self.cast_fireball()
        elif self.spell_function == 'lightning':
            self.cast_lightning() 
        elif self.spell_function == 'confusion':
            self.cast_confuse()"""
        
            
    def cast_heal(self, game_msgs, player):
        #heal the player
        if player.fighter.hp == player.fighter.max_hp:
            message('You are already at full health.', game_msgs, libtcod.red)
            message(str(player.fighter.max_hp) + ' is max hp.', game_msgs)
            return 'cancelled'
     
        message('Your wounds start to feel better!', game_msgs, libtcod.light_violet)
        self.player.fighter.heal(7)
     
    """def cast_lightning(self):
        #find closest enemy (inside a maximum range) and damage it
        monster = closest_monster(LIGHTNING_RANGE)
        if monster is None:  #no enemy found within maximum range
            message('No enemy is close enough to strike.', libtcod.red)
            return 'cancelled'
     
        #zap it!
        message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
            + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
        monster.fighter.take_damage(LIGHTNING_DAMAGE)
     
    def cast_fireball(self):
        #ask the player for a target tile to throw a fireball at
        message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
        (x, y) = target_tile()
        if x is None: return 'cancelled'
        message('The fireball explodes, burning everything within ' + str(3) + ' tiles!', libtcod.orange)
     
        for obj in objects:  #damage every fighter in range, including the player
            if obj.distance(x, y) <= 3 and obj.fighter:
                message('The ' + obj.name + ' gets burned for ' + str(12) + ' hit points.', libtcod.orange)
                obj.fighter.take_damage(12)
     
    def cast_confuse(self):
        #ask the player for a target to confuse
        message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
        monster = target_monster(CONFUSE_RANGE)
        if monster is None: return 'cancelled'
     
        #replace the monster's AI with a "confused" one; after some turns it will restore the old AI
        old_ai = monster.ai
        monster.ai = ConfusedMonster(old_ai)
        monster.ai.owner = monster  #tell the new component who owns it
        message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)"""