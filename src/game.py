import libtcodpy as libtcod
import math
import textwrap
import shelve
import pygame
import sys, os
from Room import *
from Tile import *
from Fighter import *
from AI import *
from Spells import *
from Message import *
from Dungeon import *
from Item import *
 
#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
 
#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
 
#spell values
HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
 
FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 10
LIGHTER_TORCH_RADIUS = 8
LIGHTEST_TORCH_RADIUS = 5
 
LIMIT_FPS = 20  #20 frames-per-second maximum
 
color_dark_wall = libtcod.Color(0, 0, 0)
color_light_wall = libtcod.Color(100, 70, 50)
color_light_wall2 = libtcod.Color(30, 20, 15)
color_dark_ground = libtcod.Color(20, 20, 20)

color_light_ground = libtcod.Color(100, 75, 50)
color_light_ground2 = libtcod.Color(150, 120, 70)
color_light_ground3 = libtcod.Color(200, 150, 100)

color_outside = libtcod.Color(0, 0, 0)

LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30
 
class game_object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None, always_visible=False, equipment=None, inventory=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self
        self.always_visible = always_visible
        self.equipment = equipment
        if self.equipment:
            self.equipment.owner = self
            self.item = Item()
            self.item.owner = self
        self.inventory = inventory
 
    def move(self, dx, dy):
        global dungeon, objects
        #move by the given amount, if the destination is not blocked
        if not dungeon.is_blocked(self.x + dx, self.y + dy, objects):
            self.x += dx
            self.y += dy
            
        
    def get_all_equipped(self):
        if self.name == 'player':
            equipped_list = []
            for item in self.inventory:
                if item.equipment and item.equipment.is_equipped:
                    equipped_list.append(item.equipment)
            return equipped_list
        else:
            return []
 
    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        abs_x = abs(dx)
        abs_y = abs(dy)
        if abs_x + abs_y == 3 and abs_x > 0 and abs_y > 0:
            if dx > dy:
                dx = 0
                dy = dy / distance
                if dy > 0:
                    dy = 1
                else:
                    dy = -1
            else:
                dy = 0
                dx = dx / distance
                if dx > 0:
                    dx = 1
                else:
                    dx = -1
        else:
            dx = int(round(dx / distance))
            dy = int(round(dy / distance))
        self.move(dx, dy)
 
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)
 
    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
 
    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global objects
        objects.remove(self)
        objects.insert(0, self)
 
    def draw(self):
        #only show if it's visible to the player
        if libtcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and dungeon.get_dungeon()[self.x][self.y].explored):
            #set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)
        
    def get_x(self):
        return self.x
    
    def get_y(self):
        return self.y
    
    def set_cords(self, x, y):
        self.x = x
        self.y = y
 
 
def make_map():
    global dungeon, objects, stairs, dungeon_levels, upstairs
 
    #the list of objects with just the player
    objects = [player]
 
    #fill map with "blocked" tiles
    dungeon = Dungeon(MAP_HEIGHT, MAP_WIDTH)
 
    rooms = []
    num_rooms = 0
 
    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
 
        #Room class makes rectangles easier to work with
        new_room = Room(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
 
        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            dungeon.create_room(new_room)
 
            #add some contents to this room, such as monsters
            place_objects(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_rooms == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
                upstairs = game_object(new_x, new_y, '>', 'upstairs', libtcod.white, always_visible=True)
                objects.append(upstairs)
                upstairs.send_to_back()
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel
 
                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()
 
                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    dungeon.create_h_tunnel(prev_x, new_x, prev_y)
                    dungeon.create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    dungeon.create_v_tunnel(prev_y, new_y, prev_x)
                    dungeon.create_h_tunnel(prev_x, new_x, new_y)
 
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1               
    stairs = game_object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()#Drawn under monsters
    dungeon_levels.append(dungeon)
 
 
def place_objects(room):
    #choose random number of monsters
    max_monsters = from_dungeon_level([[2, 1], [3, 2], [5, 4]])
    monster_chances = {}
    monster_chances['orc'] = 80
    monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
    monster_chances['emperor moloch'] = from_dungeon_level([[10, 5], [50, 7]])
    max_items = from_dungeon_level([[1, 1], [2, 4]])
    item_chances = {}
    item_chances['heal'] = 40
    item_chances['sword'] = 10
    item_chances['armor'] = 10
    item_chances['shit'] = 10
    
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not dungeon.is_blocked(x, y, objects):
            choice = random_choice(monster_chances)
            if choice == 'orc':
                #create an orc
                fighter_component = Fighter(hp=20, defense=0, power=4, xp=70, death_function=monster_death)
                ai_component = BasicMonster(player)
                monster = game_object(x, y, 'o', 'orc', libtcod.desaturated_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'troll':
                #create a troll
                fighter_component = Fighter(hp=30, defense=2, power=8, xp=99, death_function=monster_death)
                ai_component = BasicMonster(player)
                monster = game_object(x, y, 'T', 'troll', libtcod.darker_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'emperor moloch':
                #Kill player lol
                fighter_component = Fighter(hp=200, defense=5, power=20, xp=999, death_function=monster_death)
                ai_component = BasicMonster(player)
                monster = game_object(x, y, '&', 'emperor moloch', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster)
 
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not dungeon.is_blocked(x, y, objects):
            choice = random_choice(item_chances)
            if choice == 'heal':
                #create a healing potion (70% chance)
                item_component = Item(spell=Spell(3, player, 'heal'))
 
                item = game_object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
            elif choice == 'sword':
                equipment_component = Equipment(slot='right hand', power_bonus=3)
                item = game_object(x, y, '/', 'rusty dagger', libtcod.sky, equipment=equipment_component)
            elif choice == 'armor':
                equipment_component = Equipment(slot='chest', defense_bonus=4)
                item = game_object(x, y, '*', 'rugged leather armor', libtcod.brass, equipment=equipment_component)
            elif choice == 'shit':
                item_component = Item()
                item = game_object(x, y, '+', 'dogshit', libtcod.red, item=item_component)
            objects.append(item)
            item.send_to_back()  #items appear below other objects
            """elif dice < 70+10:
                #create a lightning bolt scroll (10% chance)
                item_component = Item(use_function=cast_lightning)
 
                item = game_object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
            elif dice < 70+10+10:
                #create a fireball scroll (10% chance)
                item_component = Item(use_function=cast_fireball)
 
                item = game_object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
            else:
                #create a confuse scroll (10% chance)
                    item_component = Item(use_function=cast_confuse)
 
                item = game_object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)"""
 
                
 
 
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
 
    #now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
 
    #finally, some centered text with the values
    libtcod.console_set_default_foreground(panel, libtcod.dark_red)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
        name + ': ' + str(value) + '/' + str(maximum))
 
def get_names_under_mouse():
    global mouse
 
    #return a string with the names of all objects under the mouse
    (x, y) = (mouse.cx, mouse.cy)
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
        if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
 
    names = ', '.join(names)  #join the names, separated by commas
    return names.capitalize()
 
def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute
 
    if fov_recompute:
        #recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        libtcod.map_compute_fov(fov_map2, player.x, player.y, LIGHTER_TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        libtcod.map_compute_fov(fov_map3, player.x, player.y, LIGHTEST_TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        if world_loc == False:
            #go through all tiles, and set their background color according to the FOV
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    visible = libtcod.map_is_in_fov(fov_map, x, y)
                    wall = dungeon.get_dungeon()[x][y].block_sight
                    if not visible:
                        #if it's not visible right now, the player can only see it if it's explored
                        if dungeon.get_dungeon()[x][y].explored:
                            if wall:
                                libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                            else:
                                libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                    else:
                        #visible
                        lightest = libtcod.map_is_in_fov(fov_map3, x, y)
                        lighter = libtcod.map_is_in_fov(fov_map2, x, y)
                        if wall and lightest:
                            libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                        elif wall:
                            libtcod.console_set_char_background(con, x, y, color_light_wall2, libtcod.BKGND_SET)
                        elif lightest:
                            libtcod.console_set_char_background(con, x, y, color_light_ground3, libtcod.BKGND_SET)
                        elif lighter:
                            libtcod.console_set_char_background(con, x, y, color_light_ground2, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
                        dungeon.get_dungeon()[x][y].explored = True
        else:
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    visible = libtcod.map_is_in_fov(fov_map, x, y)
                    wall = dungeon.get_dungeon()[x][y].block_sight
                    if not visible:
                        #if it's not visible right now, the player can only see it if it's explored
                        if dungeon.get_dungeon()[x][y].explored:
                            if wall:
                                libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                            else:
                                libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                    else:
                        #visible
                        libtcod.console_set_char_background(con, x, y, color_outside, libtcod.BKGND_SET)
                        dungeon.get_dungeon()[x][y].explored = True
 
    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for obj in objects:
        if obj != player:
            obj.draw()
    player.draw()
 
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
 
 
    #prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)
 
    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1
 
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'Life', player.fighter.hp, player.fighter.max_hp,
        libtcod.crimson, libtcod.dark_yellow)
    if dungeon_level == 1:
        libtcod.console_set_default_foreground(panel, libtcod.light_green)
        libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'World map')
    else:
        libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon lvl ' + str(dungeon_level - 1))
 
    #display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
 
def player_move_or_attack(dx, dy):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for obj in objects:
        if obj.fighter and obj.x == x and obj.y == y:
            target = obj
            break
 
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target, game_msgs, player)
    else:
        player.move(dx, dy)
        fov_recompute = True
 
 
def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
 
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
 
    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
 
    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
 
    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None
 
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            name = item.name
            if item.equipment and item.equipment.is_equipped:
                name = name + ' (on ' + item.equipment.slot + ')'
            options.append(name)
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item
 
def msgbox(text, width=50):
    menu(text, [], width)  #use menu() as a sort of "message box"
 
def handle_keys():
    global key;
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
 
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game
 
    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
            player_move_or_attack(0, -1)
 
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
            player_move_or_attack(0, 1)
 
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
            player_move_or_attack(-1, 0)
 
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
            player_move_or_attack(1, 0)
        elif key.vk == libtcod.KEY_KP7:
            player_move_or_attack(-1, -1)
        elif key.vk == libtcod.KEY_KP9:
            player_move_or_attack(1, -1)
        elif key.vk == libtcod.KEY_KP1:
            player_move_or_attack(-1, 1)
        elif key.vk == libtcod.KEY_KP3:
            player_move_or_attack(1, 1)
        elif key.vk == libtcod.KEY_KP5:
            pass
        else:
            #test for other keys
            key_char = chr(key.c)
 
            if key_char == ',':
                #pick up an item
                for obj in objects:  #look for an item in the player's tile
                    if obj.x == player.x and obj.y == player.y and obj.item:
                        obj.item.pick_up(inventory, objects, game_msgs)
                        break
 
            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use(inventory, game_msgs, player)
                else:
                    message('Did nothing', game_msgs)
 
            if key_char == 'd':
                #show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop(inventory, objects, game_msgs, player)
                else:
                    message('Nothing was dropped', game_msgs)
            if key_char == '<':
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
            if key_char == '>':
                if not upstairs == None:
                    if upstairs.x == player.x and upstairs.y == player.y:
                        go_up()
            if key_char == 'c':
                level_up_xp = LEVEL_UP_BASE + player.level*LEVEL_UP_FACTOR
                msgbox('Character information\n\nLEVEL: ' + str(player.level) + 
                       '\nXP: ' + str(player.fighter.xp) + 
                       '\nXP TO LVL UP: ' + str(level_up_xp) + 
                       '\nMAX HP: ' + str(player.fighter.max_hp) + 
                       '\nSTRENGHT ' + str(player.fighter.power) + 
                       '\nDEFENCE ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
 
            return 'didnt-take-turn'
 
def player_death(player):
    #the game ended!
    global game_state
    message('You died!', game_msgs, libtcod.red)
    game_state = 'dead'
 
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
 
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(monster.name.capitalize() + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', game_msgs, libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
 
def target_tile(max_range=None):
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    global key, mouse
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
        render_all()
        (x, y) = (mouse.cx, mouse.cy)
 
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None)  #cancel if the player right-clicked or pressed Escape
 
        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
            (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)
 
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None
 
        #return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj
 
def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range
 
    for obj in objects:
        if obj.fighter and not obj == player and libtcod.map_is_in_fov(fov_map, obj.x, obj.y):
            #calculate distance between this object and the player
            dist = player.distance_to(obj)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = obj
                closest_dist = dist
    return closest_enemy
 

 
def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    savefile = shelve.open('save', 'n')
    savefile['dungeon'] = dungeon
    savefile['objects'] = objects
    savefile['player_index'] = objects.index(player)  #index of player in objects list
    savefile['inventory'] = inventory
    savefile['game_msgs'] = game_msgs
    savefile['game_state'] = game_state
    savefile['stairs_index'] = objects.index(stairs)
    if not upstairs == None:
        savefile['upstairs_index'] = objects.index(upstairs)
    else:
        savefile['upstairs_index'] = None
    savefile['dungeon_level'] = dungeon_level
    savefile['dungeon_levels'] = dungeon_levels
    savefile['level_objects'] = level_objects
    savefile['world_loc'] = world_loc
    savefile.close()
 
def load_game():
    #open the previously saved shelve and load the game data
    global dungeon, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level, dungeon_levels, upstairs, level_objects, world_loc
    loadfile = shelve.open('save', 'r')
    dungeon = loadfile['dungeon']
    objects = loadfile['objects']
    player = objects[loadfile['player_index']]  #get index of player in objects list and access it
    inventory = loadfile['inventory']
    game_msgs = loadfile['game_msgs']
    game_state = loadfile['game_state']
    stairs = objects[loadfile['stairs_index']]
    upstairs_in = loadfile['upstairs_index']
    if not upstairs_in == None:
        upstairs = objects[upstairs_in]
    else:
        upstairs = None
    dungeon_level = loadfile['dungeon_level']
    dungeon_levels = loadfile['dungeon_levels']
    level_objects = loadfile['level_objects']
    world_loc = loadfile['world_loc']
    loadfile.close()
    os.remove('save')
    initialize_fov()
 
def new_game():
    global player, inventory, game_msgs, game_state, dungeon_level, dungeon_levels, level_objects, dungeon, objects, world_loc, stairs
    inventory = []
    dungeon_levels = []
    level_objects = []
    worldmap = open("worldmap.txt")
    lines = worldmap.readlines()
    he = 0
    wi = 0
    for i in lines:
        if i.startswith('#HEIGHT'):
            s = i.split(' ')
            he = int(s[1])
        if i.startswith('#WIDTH'):
            s = i.split(' ')
            wi = int(s[1])
    world = Dungeon(he, wi)
    x = 0
    y = 0
    #create object representing the player
    fighter_component = Fighter(hp=30, defense=2, power=5, xp=0, death_function=player_death)
    player = game_object(73, 2, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component, inventory=inventory)
    player.level = 1
    objects = [player]
    for i in lines:
        if not i.startswith('#') and y < (len(lines) - 3): #Meaning it's map data
            x = 0
            i = i.strip('\n')
            for z in i:
                if not z == '^':
                    world.get_dungeon()[x][y].blocked = False
                    world.get_dungeon()[x][y].block_sight = False
                    if z == '&':
                        wmo = game_object(x, y, z, 'Tree', libtcod.green)
                    elif z == 'o':
                        stairs = game_object(x, y, z, 'stairs', libtcod.light_blue)
                        objects.append(stairs)
                        stairs.send_to_back()
                    elif z == '"':
                        wmo = game_object(x, y, z, 'grass', libtcod.dark_green)
                    else:
                        wmo = game_object(x, y, z, 'plain', libtcod.brass)
                    objects.append(wmo)
                    wmo.send_to_back()
                else:
                    wmo = game_object(x, y, z, 'mountain', libtcod.grey, blocks=True)
                    objects.append(wmo)
                x += 1
            y += 1
    dungeon = world
    dungeon_levels.append(dungeon)
    world_loc = True
    
 
    #generate dungeon (at this point it's not drawn to the screen)
    dungeon_level = 1
    #make_map()
    initialize_fov()
 
    game_state = 'playing'
    
    #create the list of game messages and their colors, starts empty
    game_msgs = []
 
    #a warm welcoming message!
    message('A light breeze. Sunny.', game_msgs, libtcod.red)
    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = game_object(0, 0, '-', 'rusty dagger', libtcod.sky, equipment=equipment_component)
    inventory.append(obj)
    equipment_component.equip(game_msgs, inventory)
    obj.always_visible = True
    
def next_level():
    global dungeon_level, dungeon, objects, level_objects, world_loc, stairs, upstairs
    dungeon_level += 1
    objects.remove(player)
    if world_loc == True:
        world_loc = False
    if len(dungeon_levels) >= dungeon_level:
        message('You go down... Again.', game_msgs, libtcod.light_lime)
        dungeon = dungeon_levels[dungeon_level - 1]
        objects = level_objects[dungeon_level - 1]
        player_x = None
        player_y = None
        for i in objects:
            if i.name == 'upstairs':
                upstairs = i
                player_x = i.get_x()
                player_y = i.get_y()
            elif i.name == 'stairs':
                stairs = i
        player.set_cords(player_x, player_y)
        initialize_fov()
    else:
        level_objects.append(objects)
        message('Once again, you are wrapped in darkness as you progress deeper into the dungeon...', game_msgs, libtcod.light_chartreuse)
        make_map()
        initialize_fov()
    
def go_up():
    global dungeon_level, objects, dungeon, level_objects, player, stairs, upstairs, world_loc
    level_objects.append(objects)
    message('You slowly ascend the stairs...', game_msgs, libtcod.light_azure)
    dungeon_level -= 1
    dungeon = dungeon_levels[dungeon_level - 1]
    objects = level_objects[dungeon_level - 1]
    objects.append(player)
    player_x = None
    player_y = None
    for i in objects:
        if i.name == 'stairs':
            stairs = i
            player_x = i.get_x()
            player_y = i.get_y()
        elif i.name == 'upstairs':
            upstairs = i
    if dungeon_level == 1:
        world_loc = True
        upstairs = None #Can't go to heaven :(
    player.set_cords(player_x, player_y)
    initialize_fov()
    
def random_choice(chances_dict):
    chances = chances_dict.values()
    strings = chances_dict.keys()
    return strings[random_choice_index(chances)]
    
def random_choice_index(chances):
    dice = libtcod.random_get_int(0, 1, sum(chances))
    running_sum = 0
    choice = 0
    for z in chances:
        running_sum += z
        if dice <= running_sum:
            return choice
        choice+=1
    
def check_level_up():
    level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    if player.fighter.xp >= level_up_xp:
        player.level += 1
        player.fighter.xp -= level_up_xp
        message('Your efforts are paying off. You reached level ' + str(player.level) + '!', game_msgs, libtcod.light_yellow)
        choice = None
        stat_points = player.level + 1
        while stat_points > 0:
            choice = menu('LEVEL UP! You have ' + str(stat_points) + ' stat points to spend!\n', ['Str ' + str(player.fighter.power), 'Def ' + str(player.fighter.defense), 
                          'Hit points ' + str(player.fighter.max_hp)], LEVEL_SCREEN_WIDTH)
            if choice == 0:
                player.fighter.base_power += 1
                stat_points -= 1
            elif choice == 1:
                player.fighter.base_defense += 1
                stat_points -= 1
            elif choice == 2:
                player.fighter.base_max_hp += 5
                player.fighter.hp += 5
                stat_points -= 1
                
def from_dungeon_level(table):
    for (v, l) in reversed(table):
        if dungeon_level >= l:
            return v
    return 0
 
def initialize_fov():
    global fov_recompute, fov_map, fov_map2, fov_map3
    fov_recompute = True
 
    #create 3 fovs for some enhanced graphical effects :)
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not dungeon.get_dungeon()[x][y].block_sight, not dungeon.get_dungeon()[x][y].blocked)
    fov_map2 = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map2, x, y, not dungeon.get_dungeon()[x][y].block_sight, not dungeon.get_dungeon()[x][y].blocked)
    fov_map3 = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map3, x, y, not dungeon.get_dungeon()[x][y].block_sight, not dungeon.get_dungeon()[x][y].blocked)
 
    libtcod.console_clear(con)  #unexplored areas start black (which is the default background color)
 
def play_game():
    global key, mouse
 
    player_action = None
 
    mouse = libtcod.Mouse()
    key = libtcod.Key()
    pygame.mixer.music.load('cave.mp3')
    pygame.mixer.music.play(1)
    while not libtcod.console_is_window_closed():
        #render the screen
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
        render_all()
 
        libtcod.console_flush()
        check_level_up()
 
        #erase all objects at their old locations, before they move
        for obj in objects:
            obj.clear()
 
        #handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break
 
        #let monsters take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for obj in objects:
                if obj.ai:
                    obj.ai.take_turn(game_msgs)
 
def main_menu():
    img = libtcod.image_load('menu_bg2.png')
    pygame.mixer.music.load('ultima_theme.mp3')
    
 
    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)
        pygame.mixer.music.play(1)
        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.light_purple)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
            'ROGUELIKE FOR THE TKK PYTHON COURSE')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
            'Made by 79040A')
 
        #show options and wait for the player's choice
        choice = menu('', ['NEW GAME', 'LOAD GAME', 'QUIT'], 24)
 
        if choice == 0:  #new game
            new_game()
            play_game()
        if choice == 1:  #load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2:  #quit
            break
 
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Roguelike', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
game_msgs = []
dungeon_levels = []
level_objects = []
upstairs = None
stairs = None
player = None
pygame.init()
pygame.mixer.init()
 
main_menu()