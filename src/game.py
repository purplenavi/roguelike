import libtcodpy as libtcod
import math
import textwrap
import shelve
import pygame
import sys, os, time
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

LEVEL_UP_BASE = 50
LEVEL_UP_FACTOR = 70
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30

class quest:
    #simple class to keep track of quest data
    def __init__(self, description, monsters_to_kill, message_after_completion, exp, quest_giver, special_monster = None):
        self.description = description
        self.monsters_to_kill = monsters_to_kill
        self.message_after_completion = message_after_completion
        self.exp = exp
        self.quest_giver = quest_giver
        self.special_monster = None
        self.killed = 0
        self.complete = False
        
    def increment_kill(self, game_msgs):
        self.killed += 1
        self.quest_complete(game_msgs)
        
    def quest_complete(self, game_msgs):
        if self.killed == self.monsters_to_kill:
            self.complete = True
            message('Quest ' + self.description + ' complete!', game_msgs)
 
class game_object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None, always_visible=False, equipment=None, inventory=None, talks = None):
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
        self.talks = talks
 
    def move(self, dx, dy):
        global dungeon, objects
        #move by the given amount, if the destination is not blocked
        if not dungeon.is_blocked(self.x + dx, self.y + dy, objects):
            self.x += dx
            self.y += dy
            
    def move_through(self, dx, dy):
        global dungeon, objects
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
    dungeon_levels[dungeon_level] = dungeon
 
def random_battle_place_objects():
    monster_data = open('monsters.data')
    monzters = []
    for mon in monster_data:
        if not mon.startswith('#'):
            monstr = mon.split('#')
            monstr = [item.strip() for item in monstr]
            monzters.append(monstr)
    group_size = libtcod.random_get_int(0, 1, 3)
    group_name = None
    group_n = None
    if group_size == 1:
        group_name = 'group'
        group_n = 6
    elif group_size == 2:
        group_name = 'pack'
        group_n = 12
    else:
        group_name = 'horde'
        group_n = 25
    monster_type = monzters[libtcod.random_get_int(0, 0, len(monzters) - 1)]

    for z in range(0, group_n):
        while 1:
            x = libtcod.random_get_int(0, 4, MAP_WIDTH - 4)
            y = libtcod.random_get_int(0, 4, MAP_HEIGHT - 4)
            if not dungeon.is_blocked(x, y, objects):
                break
        fighter_component = Fighter(hp=int(monster_type[3]), defense=int(monster_type[2]), power=int(monster_type[1]), xp=int(monster_type[4]), death_function=monster_death)
        ai_component = BasicMonster(player)
        monster = game_object(x, y, monster_type[5], monster_type[0], monster_colors[monster_type[6]], blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(monster)
    message('You encounter a wandering ' + group_name + ' of ' + monster_type[0] + 's.', game_msgs, libtcod.red)
        
 
def place_objects(room):
    #choose random number of monsters
    monster_data = open('monsters.data')
    monzters = []
    for mon in monster_data:
        if not mon.startswith('#'):
            mons = mon.split('#')
    max_monsters = from_dungeon_level([[2, 1], [3, 2], [5, 4]])
    monster_chances = {}
    monster_chances['orc'] = 80
    monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
    monster_chances['emperor moloch'] = from_dungeon_level([[10, 5], [50, 7]])
    max_items = from_dungeon_level([[1, 1], [2, 4]])
    
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
            item = generate_item(x, y)
            objects.append(item)
 
def generate_item(x, y):
    item_file = open('items.data')
    all_items = []
    total_chance = 0
    for line in item_file:
        if not line.startswith('#'):
            line = line.split('#')
            tmp_item = []
            name = line[0]
            char = line[1]
            color = line[2]
            chance = int(line[3])
            level = int(line[4])
            use_f = line[5]
            total_chance += chance
            tmp_item.append(name)
            tmp_item.append(char)
            tmp_item.append(color)
            tmp_item.append(chance)
            tmp_item.append(level)
            tmp_item.append(use_f)
            all_items.append(tmp_item)
    rand_number = libtcod.random_get_int(0, 1, total_chance)
    off_chance = 0
    item = None
    for i in all_items:
        chance = i[3]
        increase_off = chance
        chance += off_chance
        off_chance += increase_off
        if chance >= rand_number:
            uf = i[5]
            uf = uf.strip()
            uf = uf.split('-')
            level = i[4]
            if uf[0] == 'equip':
                for key in item_properties:
                    if key in i[0]:
                        value = item_properties[key]
                        if value == 'power':
                            equipment_component = Equipment(slot=uf[1], power_bonus = level)
                            break
                        if value == 'defense':
                            equipment_component = Equipment(slot=uf[1], defense_bonus = level)
                            break
                        if value == 'magic':
                            pass
                item = game_object(x, y, i[1], i[0], i[2], equipment=equipment_component)
                break
            else: #usable item
                item_component = Item(spell=Spell(3, player, uf[0]))
                item = game_object(x, y, i[1], i[0], i[2], item=item_component)
                break
    return item
 
 
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
    libtcod.console_set_default_foreground(panel, libtcod.black)
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
        libtcod.green, libtcod.dark_red)
    if dungeon_level == 1:
        libtcod.console_set_default_foreground(panel, libtcod.light_green)
        libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'World map')
    elif dungeon_level == 0:
        libtcod.console_set_default_foreground(panel, libtcod.dark_red)
        libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'BATTLE!')
    elif player_in_town:
        libtcod.console_set_default_foreground(panel, libtcod.sky)
        libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, dungeon_level)
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
    
    if game_state == 'targeting':
        move_target()
 
    if game_state == 'playing':
        #movement keys, this could use some more work to make it more clear, but as of now i have no time :(
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
            player_move_or_attack(0, -1)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
 
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
            player_move_or_attack(0, 1)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
 
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
            player_move_or_attack(-1, 0)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
 
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
            player_move_or_attack(1, 0)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
                
        elif key.vk == libtcod.KEY_KP7:
            player_move_or_attack(-1, -1)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
                
        elif key.vk == libtcod.KEY_KP9:
            player_move_or_attack(1, -1)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
                
        elif key.vk == libtcod.KEY_KP1:
            player_move_or_attack(-1, 1)
            if dungeon_level == 1:
                create_world_message()
                random_battle() 
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
                
        elif key.vk == libtcod.KEY_KP3:
            player_move_or_attack(1, 1)
            if dungeon_level == 1:
                create_world_message()
                random_battle()
            if player_in_town:
                leave_town()
            if dungeon_level == 0:
                leave_random()
                
        elif key.vk == libtcod.KEY_KP5:
            if dungeon_level == 1:
                create_world_message()
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
            if key_char == 't':
                create_target_object(player.x, player.y)
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
                for obj in objects:
                    if obj.x == player.x and obj.y == player.y and obj.char == 'O':
                        enter_town(player.x, player.y)
            if key_char == '>':
                for u in objects:
                    if u.name == 'upstairs':
                        if upstairs.x == player.x and upstairs.y == player.y:
                            go_up()
            if key_char == 'c':
                level_up_xp = LEVEL_UP_BASE + player.level*LEVEL_UP_FACTOR
                quests_string = '\nQuests :'
                for q in player_quests:
                    quests_string += q.description 
                    quests_string += '\nMonsters killed '
                    quests_string = quests_string + str(q.killed) + '/' + str(q.monsters_to_kill) 
                msgbox('Character information\n\nLEVEL: ' + str(player.level) + 
                       '\nXP: ' + str(player.fighter.xp) + 
                       '\nXP TO LVL UP: ' + str(level_up_xp) + 
                       '\nMAX HP: ' + str(player.fighter.max_hp) + 
                       '\nSTRENGHT ' + str(player.fighter.power) + 
                       '\nDEFENCE ' + str(player.fighter.defense) +
                       quests_string, CHARACTER_SCREEN_WIDTH)
                time.sleep(0.5)
 
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
    global objects, player_quests, game_msgs
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    monster_name = monster.name
    message(monster.name.capitalize() + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', game_msgs, libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    x = monster.x
    y = monster.y
    item = generate_item(x, y)
    objects.append(item)
    if not dungeon_level == 1:
        for q in player_quests:
            if not q.special_monster:
                q.increment_kill(game_msgs)
            if q.special_monster:
                if q.special_monster == monster_name:
                    q.increment_kill(game_msgs)
 
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
    if dungeon_level == 0:
        message('Cannot save while in battle!', game_msgs, libtcod.red)
    else:
        #open a new empty shelve (possibly overwriting an old one) to write the game data
        savefile = shelve.open('save', 'n')
        savefile['dungeon'] = dungeon
        savefile['objects'] = objects
        save_player = None
        for p in objects:
            if p.name == 'player':
                save_player = p
        savefile['player_index'] = objects.index(save_player)  #index of player in objects list
        savefile['inventory'] = inventory
        savefile['game_msgs'] = game_msgs
        savefile['game_state'] = game_state
        savefile['stairs_index'] = None
        savefile['upstairs_index'] = None
        for u in objects:
            if u.name == 'upstairs' and not player_in_town and not dungeon_level == 0:
                savefile['upstairs_index'] = objects.index(u)
            if u.name == 'stairs' and not dungeon_level == 0 and not player_in_town:
                savefile['stairs_index'] = objects.index(u)
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
    stairs_in = loadfile['stairs_index']
    upstairs_in = loadfile['upstairs_index']
    if stairs_in:
        stairs = objects[stairs_in]
    else:
        stairs = None
    if upstairs_in:
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
    
def create_world_message():
    rand_int = libtcod.random_get_int(0, 1, 10)
    if rand_int > 7:
        x = player.x
        y = player.y
        for obj in objects:
            if obj.x == x and obj.y == y and not obj.name == 'player':
                if rand_int == 8:
                    message(obj.name + '. A light breeze. Sunny.', game_msgs, libtcod.green)
                if rand_int == 9:
                    message(obj.name + '. Rain is pouring down. Cloudy.', game_msgs, libtcod.blue)
                if rand_int == 10:
                    message(obj.name + '. Perfect weather. You feel relaxed.', game_msgs, libtcod.yellow)
                 
def random_battle():
    global dungeon, objects, level_objects, dungeon_level, dungeon_levels, random_x, random_y
    
    rand_int = libtcod.random_get_int(0, 1, 12)
    if rand_int > 11:
        random_x = player.x
        random_y = player.y
        for obj in objects:
            if obj.x == random_x and obj.y == random_y and not obj.name == 'player' and not obj.name == 'stairs':
                primary_type_name = obj.name
                primary_color = obj.color
                primary_terrain = obj.char
                message('You are under attack!', game_msgs, libtcod.red)
                level_objects[dungeon_level] = objects
                dungeon_levels[dungeon_level] = dungeon
                dungeon_level = 0
                objects = [player]
                dungeon = Dungeon(MAP_HEIGHT, MAP_WIDTH)
                player.x = MAP_WIDTH / 2
                player.y = MAP_HEIGHT / 2
                for x in range(0, MAP_WIDTH - 1):
                    for y in range(0, MAP_HEIGHT - 1):
                        dungeon.get_dungeon()[x][y].blocked = False
                        dungeon.get_dungeon()[x][y].block_sight = False
                        rand_terrain = libtcod.random_get_int(0, 1, 10)
                        if rand_terrain < 8: #Primary terrain
                            ro = game_object(x, y, primary_terrain, primary_type_name, primary_color, always_visible=True)
                        else:
                            if primary_type_name == 'grass':
                                ro = game_object(x, y, '&', 'tree', libtcod.dark_green, always_visible=True)
                            else:
                                ro = game_object(x, y, '"', 'grass', libtcod.green, always_visible=True)
                        objects.append(ro)
                initialize_fov()
                random_battle_place_objects()
                break
            
def leave_random():
    global player, dungeon, dungeon_level, objects, level_objects
    if player.x < 3 or player.x > MAP_WIDTH - 3 or player.y < 3 or player.y > MAP_HEIGHT - 3:#Exit to worldmap
        dungeon_level = 1
        dungeon = dungeon_levels[dungeon_level]
        objects = level_objects[dungeon_level]
        #dungeon_levels.remove(dungeon)
        #level_objects.remove(objects)
        player.set_cords(random_x, random_y)
        initialize_fov()
                

def create_target_object(x, y):
    #This pauses the game and creates a targeting object
    global key, game_state
    game_state = 'targeting'
    targeting_object = game_object(x, y, '_', 'target', libtcod.white)
    objects.append(targeting_object)
    message('Target mode on. Move cursor with numpad keys, hit enter when cursor is in desired place', game_msgs, libtcod.white)
    
def move_target():
    #moves the target, and prints npc talk if enter is hit on top of npc
    global game_state, objects
    targeting_object = None
    for i in objects:
        if i.name == 'target':
            targeting_object = i
    #moving the target
    if key.vk == libtcod.KEY_KP8:
        targeting_object.move_through(0, -1)
        target_message()
    if key.vk == libtcod.KEY_KP7:
        targeting_object.move_through(-1, -1)
        target_message()
    if key.vk == libtcod.KEY_KP9:
        targeting_object.move_through(1, -1)
        target_message()
    if key.vk == libtcod.KEY_KP4:
        targeting_object.move_through(-1, 0)
        target_message()
    if key.vk == libtcod.KEY_KP6:
        targeting_object.move_through(1, 0)
        target_message()
    if key.vk == libtcod.KEY_KP1:
        targeting_object.move_through(-1, 1)
        target_message()
    if key.vk == libtcod.KEY_KP2:
        targeting_object.move_through(0, 1)
        target_message()
    if key.vk == libtcod.KEY_KP3:
        targeting_object.move_through(1, 1)
        target_message()
    if key.vk == libtcod.KEY_ENTER:
        #Enter pressed, continuing gameplay
        game_state = 'playing'
        for npc in objects:
            if npc.x == targeting_object.x and npc.y == targeting_object.y and not npc.name == 'player' and not npc.name == 'target' and not npc.name in lifeless_objects:
                if npc.talks:
                    #if the npc has something to say, check for quest
                    for q in player_quests:
                        #if player has quest from that npc and it's complete, call cash in quest
                        if q.quest_giver == npc.name and q.complete == True:
                            cash_complete_quest(q)
                            npc.talks = q.message_after_completion
                    message(npc.talks, game_msgs, libtcod.brass)
                    #if npc has quest to give, call create_quest
                    create_quest(npc.name)
                else:
                    message('The ' + npc.name + ' stares at you silently.', game_msgs, libtcod.gray)
        for i in objects:
            if i.name == targeting_object.name:
                objects.remove(i)
    
    fov_recompute = True
 
def target_message(): 
    #creates message for what's under the cursor atm
    tx = None
    ty = None
    for t in objects:
        if t.name == 'target':
            tx = t.x
            ty = t.y
    for t in objects:
        if t.x == tx and t.y == ty and not t.name == 'target':
            message(t.name, game_msgs, libtcod.violet)
            
def create_quest(name):
    #This moves a quest from quests to player quests
    global player_quests, quests
    for q in quests:
        if q.quest_giver == name:
            player_quests.append(q)
            quests.remove(q)
    
def cash_complete_quest(q):
    #cash in the quest, reward player with exp
    player.fighter.xp += q.exp
    player_quests.remove(q)

def new_game():
    #Constructs a new game
    global player, inventory, game_msgs, game_state, dungeon_level, dungeon_levels, level_objects, dungeon, objects, world_loc, stairs, village_objects, quests
    inventory = []
    dungeon_levels = {}
    level_objects = {}
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
                        wmo = game_object(x, y, z, 'tree', libtcod.green, always_visible=True)
                    elif z == 'o':
                        stairs = game_object(x, y, z, 'stairs', libtcod.light_blue, always_visible=True)
                        objects.append(stairs)
                        stairs.send_to_back()
                    elif z == '1' or z == '2' or z == '3' or z == '4': #And so on, basically look for numbers in the worldmap, as they represent special targets
                        world_data = open('worldmap.data')
                        fetch_data = []
                        for data_line in world_data:
                            fetch_data.append(data_line)
                        villagers = []
                        villager_obj = []
                        num = 0
                        city_h = None
                        city_w = None
                        city_name = None
                        while 1:
                            #parse all city villager data
                            if fetch_data[num].startswith('CITY') and z in fetch_data[num]:#We have a hit :)
                                tmp = fetch_data[num].strip('\n')
                                tmp = tmp.split('#')
                                city_name = tmp[2]
                                city_h = int(tmp[3])
                                city_w = int(tmp[4])
                                num += 2
                                while fetch_data[num].startswith('#'): #NPC data
                                    fetch_data[num] = fetch_data[num].strip('\n')
                                    villagers.append(fetch_data[num])
                                    num += 1
                            #parse all quest data and set it to quests
                            if fetch_data[num].startswith('QUEST') and z in fetch_data[num]:
                                while not fetch_data[num].startswith('MAP'):
                                    data = fetch_data[num].strip('\n')
                                    data = data.split('#')
                                    for key in quest_types:
                                        if key in fetch_data[num]:
                                            quest_giver = None
                                            for vi in villagers:
                                                if data[1] in vi:
                                                    quest_giver = vi.split('#')
                                                    quest_giver = quest_giver[1]
                                            q = quest(data[2], int(data[3]), data[5], int(data[4]), quest_giver)
                                            quests.append(q)
                                    num += 1
                            #parse all map data
                            if fetch_data[num].startswith('MAP') and z in fetch_data[num]: #Map data for corresponding number :)
                                city = Dungeon(city_h, city_w)
                                num += 1
                                city_x = 0
                                city_y = 0
                                while not fetch_data[num].startswith('#'):
                                    city_line = fetch_data[num].strip('\n')
                                    for c in city_line:
                                        if not c == '#':
                                            city.get_dungeon()[city_x][city_y].blocked = False
                                            city.get_dungeon()[city_x][city_y].block_sight = False
                                            if c == '1' or c == '2':
                                                for villager in villagers:
                                                    if c in villager: #Found the corresponding villager
                                                        #create quest giver npcs
                                                        d = villager.split('#')
                                                        ai = questgiver(player)
                                                        co = game_object(city_x, city_y, '.', 'grass', libtcod.green, always_visible=True)
                                                        vil = game_object(city_x, city_y, d[2], d[1], d[3], blocks=True, ai=ai, talks=d[6])
                                                        villager_obj.append(co)
                                                        villager_obj.append(vil)
                                                        villagers.remove(villager)
                                            else:
                                                if c == '=': #water
                                                    co = game_object(city_x, city_y, c, 'water', libtcod.blue, always_visible=True)
                                                if c == 'T': #tree
                                                    co = game_object(city_x, city_y, c, 'tree', libtcod.dark_green, always_visible=True)
                                                if c == '.': #grass
                                                    co = game_object(city_x, city_y, c, 'grass', libtcod.green, always_visible=True)
                                                if c == '-': #door
                                                    co = game_object(city_x, city_y, c, 'door', libtcod.green, always_visible=True)
                                                villager_obj.append(co)
                                        else:
                                            co = game_object(city_x, city_y, c, 'wall', libtcod.gray, always_visible=True)
                                            villager_obj.append(co)
                                        city_x += 1
                                    city_x = 0
                                    city_y += 1
                                    num += 1
                                while len(villagers) > 0:
                                    #randomly insert rest of the villagers
                                    rand_x = libtcod.random_get_int(0, 4, city_w - 4)
                                    rand_y = libtcod.random_get_int(0, 4, city_h - 4)
                                    if not city.is_blocked(rand_x, rand_y, villager_obj):
                                        last_guy = villagers[-1]
                                        d = last_guy.split('#')
                                        ai = NPC(player)
                                        if d[1] == 'cow':
                                            random_gibberish = libtcod.random_get_int(0, 0, len(cow_sounds) - 1)
                                            vil = game_object(rand_x, rand_y, d[2], d[1], d[3], blocks=True, ai=ai, talks=cow_sounds[random_gibberish])
                                        else:
                                            random_gibberish = libtcod.random_get_int(0, 0, len(general_phrases) - 1)
                                            vil = game_object(rand_x, rand_y, d[2], d[1], d[3], blocks=True, ai=ai, talks=general_phrases[random_gibberish])
                                        villager_obj.append(vil)
                                        villagers.remove(last_guy)
                                village_objects[city_name] = villager_obj
                                cities[city_name] = city
                            if fetch_data[num].startswith('#END'):
                                break
                            num += 1
                        wmo = game_object(x, y, 'O', city_name, libtcod.brass, always_visible=True)
                    elif z == '"':
                        wmo = game_object(x, y, z, 'grass', libtcod.dark_green, always_visible=True)
                    elif z == '=':
                        wmo = game_object(x, y, z, 'water', libtcod.blue, always_visible=True)
                    elif z == '.':
                        wmo = game_object(x, y, z, 'rocks', libtcod.gray, always_visible=True)
                    else:
                        wmo = game_object(x, y, z, 'plain', libtcod.brass, always_visible=True)
                    objects.append(wmo)
                    wmo.send_to_back()
                else:
                    wmo = game_object(x, y, z, 'mountain', libtcod.grey, blocks=True)
                    objects.append(wmo)
                x += 1
            y += 1
    dungeon = world
    dungeon_level = 1
    dungeon_levels[dungeon_level] = dungeon
    world_loc = True
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
    #function when descending the stairs
    global dungeon_level, dungeon, objects, level_objects, world_loc, stairs, upstairs
    dungeon_level += 1
    for obj in objects:
        if obj.name == 'player':
            objects.remove(obj)
    if world_loc == True:
        world_loc = False
    is_in_dungeon_levels = False
    for key in dungeon_levels:
        if key == dungeon_level:
            is_in_dungeon_levels = True
    if is_in_dungeon_levels:
        message('You go down... Again.', game_msgs, libtcod.light_lime)
        dungeon = dungeon_levels[dungeon_level]
        objects = level_objects[dungeon_level]
        objects.append(player)
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
        level_objects[dungeon_level-1] = objects
        message('Once again, you are wrapped in darkness as you progress deeper into the dungeon...', game_msgs, libtcod.light_chartreuse)
        make_map()
        initialize_fov()
    
def go_up():
    #Function when going up the stairs
    global dungeon_level, objects, dungeon, level_objects, player, stairs, upstairs, world_loc
    for i in objects:
        if i.name == 'player':
            objects.remove(i)
    level_objects[dungeon_level] = objects
    message('You slowly ascend the stairs...', game_msgs, libtcod.light_azure)
    dungeon_level -= 1
    dungeon = dungeon_levels[dungeon_level]
    objects = level_objects[dungeon_level]
    for obj in objects:
        if obj.name == 'player':
            objects.remove(obj)
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
    
def enter_town(x, y):
    #function when entering town/village, store all previous level data and fetch the current data
    global dungeon_level, dungeon, objects, level_objects, world_loc, previous_dungeon_level, player, player_in_town
    player_in_town = True
    previous_dungeon_level = dungeon_level
    town_name = None
    for obj in objects:
        if obj.x == x and obj.y == y and not obj.name == 'player':
            town_name = obj.name
    insert_to = True
    for key in dungeon_levels:
        if key == dungeon_level:
            insert_to = False
    if insert_to:
        dungeon_levels[dungeon_level] = dungeon
    level_objects[dungeon_level] = objects
    dungeon_level = town_name
    objects = village_objects[town_name]
    dungeon = cities[town_name]
    objects.append(player)
    player.set_cords(5, 5)
    initialize_fov()
    
def leave_town():
    global player, dungeon, dungeon_level, objects, level_objects, previous_dungeon_level, player_in_town
    if player.x < 3 or player.x > MAP_WIDTH - 3 or player.y < 3 or player.y > MAP_HEIGHT - 3:#Exit to worldmap
        player_in_town = False
        town_name = dungeon_level
        dungeon_level = previous_dungeon_level
        dungeon = dungeon_levels[dungeon_level]
        #dungeon_levels.remove(dungeon)
        objects = level_objects[dungeon_level]
        #level_objects.remove(objects)
        previous_dungeon_level = None
        x = None
        y = None
        for obj in objects:
            if obj.name == town_name:
                x = obj.x
                y = obj.y
        player.set_cords(x, y)
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
            time.sleep(0.5)
                
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
        libtcod.console_set_default_foreground(0, libtcod.dark_green)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
            'Shadows of the Python')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-20, libtcod.BKGND_NONE, libtcod.CENTER,
            '---A roguelike for the python course---')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-18, libtcod.BKGND_NONE, libtcod.CENTER, 'Shadows of the Python, Copyright (C) 2013 Aleksi Salonen\nShadows of the Python comes with ABSOLUTELY NO WARRANTY;\n This is free software, and you are welcome\nto redistribute it under certain conditions.')
 
        #show options and wait for the player's choice
        choice = menu('', ['NEW GAME', 'LOAD GAME', 'QUIT'], 24)
 
        if choice == 0:  #new game
            new_game()
            play_game()
        if choice == 1:  #load last game
            try:
                load_game()
                time.sleep(0.5)
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
dungeon_levels = {}
level_objects = {}
village_objects = {}
cities = {}
player_in_town = False
upstairs = None
stairs = None
player = None
random_x = None
random_y = None
previous_dungeon_level = None
monster_colors = {'green':libtcod.green, 'light_green':libtcod.light_green, 'dark_green':libtcod.dark_green, 'brass':libtcod.brass, 'dark_red':libtcod.dark_red, 'red':libtcod.red, 'gray':libtcod.gray, 'sky':libtcod.sky, 'violet':libtcod.violet, 'yellow':libtcod.yellow}
item_properties = {'sword':'power', 'dagger':'power', 'mace':'power', 'hammer':'power', 'shield':'defense', 'armour':'defense', 'cape':'defense', 'armor':'defense', 'magic':'random'}
general_phrases = ['Hello!', 'How are you doing?', 'Are you new here?', 'Day looks lovely today.', 'BRAAAAAINSSSS!']
cow_sounds = ['Moo', 'MOOooo', '....']
lifeless_objects = ['grass', 'tree', 'rocks', 'wall', 'water', 'door']
quest_types = {'kill':1}
quests = []
player_quests = []
pygame.init()
pygame.mixer.init()
 
main_menu()
