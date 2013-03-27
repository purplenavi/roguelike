'''
Created on 10.3.2013

@author: Alex
'''
from Message import *
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.death_function = death_function
        self.xp = xp
 
    @property
    def power(self):
        bonus = 0
        if self.owner.inventory:
            bonus = sum(equipment.power_bonus for equipment in self.owner.get_all_equipped())
        return self.base_power + bonus
    
    @property
    def max_hp(self):
        bonus = 0
        #if self.owner.inventory:
         #   bonus = sum(equipment.hp_bonus for equipment in self.owner.get_all_equipped())
        return self.base_max_hp + bonus
    @property
    def defense(self):
        bonus = 0
        #if self.owner.inventory and self.owner.name == 'player':
         #   bonus = sum(equipment.defense_bonus for equipment in self.owner.get_all_equipped())
        return self.base_defense + bonus
 
    def attack(self, target, game_msgs, player):
        #a simple formula for attack damage
        damage = self.power - target.fighter.defense
 
        if damage > 0:
            #make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.', game_msgs)
            target.fighter.take_damage(damage, player)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!', game_msgs)
 
    def take_damage(self, damage, player):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
 
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if not self.owner == player:
                    player.fighter.xp += self.xp
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp