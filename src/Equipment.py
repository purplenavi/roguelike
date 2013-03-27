'''
Created on 13.3.2013

@author: Alex
'''
from Message import *
import libtcodpy as libtcod
class Equipment:
    def __init__(self, slot, power_bonus=0, defense_bonus=0, hp_bonus=0):
        self.slot = slot
        self.is_equipped = False
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.hp_bonus = hp_bonus
        
    def toggle_equip(self, game_msgs, inventory):
        if self.is_equipped:
            self.dequip(game_msgs)
        else:
            self.equip(game_msgs, inventory)
    
    def equip(self, game_msgs, inventory):
        already_equipped = self.get_equipped_in_slot(self.slot, inventory)
        if already_equipped == None:
            self.is_equipped = True
            message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', game_msgs, libtcod.light_blue)
        else:
            message('Already equipping stuff in slot: ' + self.slot + '!', game_msgs, libtcod.light_red) 
        
    def dequip(self, game_msgs):
        self.is_equipped = False
        message('Removed ' + self.owner.name + ' from ' + self.slot + '.', game_msgs, libtcod.light_red)
        
    def get_equipped_in_slot(self, slot, inventory):
        for obj in inventory:
            if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
                return obj.equipment
        return None