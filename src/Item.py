'''
Created on 10.3.2013

@author: Alex
'''
from Message import *
from Equipment import *
class Item:
    #an item that can be picked up and used.
    def __init__(self, spell=None, edible=None):
        self.spell = spell
        self.edible = None
 
    def pick_up(self, inventory, objects, game_msgs):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', game_msgs, libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', game_msgs, libtcod.green)
 
    def drop(self, inventory, objects, game_msgs, player):
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        if self.owner.equipment:
            self.owner.equipment.dequip(game_msgs)
        message('You dropped a ' + self.owner.name + '.', game_msgs, libtcod.yellow)
 
    def use(self, inventory, game_msgs, player):
        #just call the "use_function" if it is defined
        if self.owner.equipment:
            self.owner.equipment.toggle_equip(game_msgs, inventory)
            return
        if self.edible:
            print 'blaa'
        if self.spell:
            number_left = self.spell.cast_spell(game_msgs, player)
            if number_left == 0:
                inventory.remove(self.owner)
        else:
            message('The ' + self.owner.name + ' cannot be used.', game_msgs)