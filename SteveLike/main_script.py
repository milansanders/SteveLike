# Robins great adventure.
# A game by Xenoxinius (Idea, humor and such) & Melinator95 (programming, keeping it real and do-able)
#
# Made possible with the roguelike tutorial on roguebasin by Jotaf
# Many thanks and praises to you good sir!

import libtcodpy as libtcod
import math
import textwrap
import shelve
import time
import String


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
CHARACTER_SCREEN_WIDTH = 30
LEVEL_SCREEN_WIDTH = 40

#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

#spell values
LIGHTNING_DAMAGE = 40
LIGHTNING_RANGE = 5
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 2
FIREBALL_DAMAGE = 25
 
#experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150
 
 
FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 10
 
LIMIT_FPS = 10  #10 frames-per-second maximum

PLAYER_NAMES = ['Robin', 'Crowbin', 'Ronifst', 'Clemens']
CLASSES = ['Super Saiyan 3', 'Toverknol', 'Pikkendief', 'Paardenridder', 'Boogschutter', 'Sterrenkundige']
 
#Starting color values
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

#Here be stairs before boss death
stair_x = -1
stair_y = -1
 
class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
 
        #all tiles start unexplored
        self.explored = False
 
        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
 
class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
 
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)
 
    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)
 
class Object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None, spell=None, stackable=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible
        
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self
 
        self.equipment = equipment
        if self.equipment:  #let the Equipment component know who owns it
            self.equipment.owner = self
 
            #there must be an Item component for the Equipment component to work properly
            if not self.item:
                self.item = Item()
            self.item.owner = self
        
        self.spell = spell
        if self.spell:  #let the Spell component know who owns it
            self.spell.owner = self
        
        self.stackable = stackable
        if self.stackable:  #let the Stackable component know who owns it
            self.stackable.owner = self
 
    @property
    def full_name(self):
        output = self.name
        if self.fighter:
            if self.fighter.player_class != None:
                output = output + ' de ' + self.fighter.player_class
        return output
    
    def move(self, dx, dy):
        #move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
 
    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
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
        #only show if it's visible to the player; or it's set to "always visible" and on an explored tile
        if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
                (self.always_visible and map[self.x][self.y].explored)):
            #set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_put_char_ex(con, self.x, self.y, '.', color_light_ground, libtcod.black)
 
 
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, money_amount=0, mp=1, dodge=0, crit_chance=0, crit_dmg=150, death_function=None, player_class=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_max_mp = mp
        self.mp = mp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        self.base_dodge = dodge
        self.base_crit_chance = crit_chance
        self.base_crit_dmg = crit_dmg #dmg=power*(crit_dmg/100)
        self.money_amount = money_amount
        self.player_class = player_class
 
    @property
    def power(self):  #return actual power, by summing up the bonuses from all equipped items
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus
 
    @property
    def defense(self):  #return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus
    
    @property
    def dodge(self): #return actual dodge chance, by summing up the bonuses from all equipped items
        bonus = sum(equipment.dodge_bonus for equipment in get_all_equipped(self.owner))
        return self.base_dodge + bonus
    
    @property
    def crit_chance(self): #return actual crit chance, by summing up the bonuses from all equipped items
        bonus = sum(equipment.crit_chance_bonus for equipment in get_all_equipped(self.owner))
        return self.base_crit_chance + bonus
    
    @property
    def crit_dmg(self): #return actual crit damage, by summing up the bonuses from all equipped items
        bonus = sum(equipment.crit_dmg_bonus for equipment in get_all_equipped(self.owner))
        return self.base_crit_dmg + bonus
 
    @property
    def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus
    
    @property
    def max_mp(self):  #return actual max_mp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_mp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_mp + bonus
 
    def attack(self, target):
        #a simple formula for attack damage
        damage = self.power - target.fighter.defense
        
        dodge_dice = libtcod.random_get_int(0, 1, 100)
        print "dodge dice: "+str(dodge_dice)
        crit_dice = libtcod.random_get_int(0, 1, 100)
        print "crit dice: "+str(crit_dice)
        if (crit_dice > self.crit_chance):
            damage = int(damage * (self.crit_dmg // 100))
        if (dodge_dice > target.fighter.dodge):
            if damage > 0:
                #make the target take some damage
                if not (crit_dice <= self.crit_chance):
                    message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
                else:
                    message(self.owner.name.capitalize() + ' rolls a 20 against ' + target.name + ' for ' + str(damage) + ' hit points.')
                target.fighter.take_damage(damage)
            else:
                message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has little effect!')
                target.fighter.take_damage(1) #At least take some dmg, swarms are dangerous!
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but misses!')
 
    def take_damage(self, damage):
        #apply damage if possible
        if (damage > 0):
            self.hp -= damage
 
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
 
                if self.owner != player:  #yield experience to the player
                    player.fighter.xp += self.xp
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
    
    def restore(self, amount):
        #Restore MP by given amount
        self.mp += amount
        if self.mp > self.max_mp:
            self.mp = self.max_mp
            
class BasicMonster:
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
 
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
 
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
 
class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
 
        else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)

class IdleMonster:
    #AI for a temporary idle monster (blinded, while in stealth, ...)
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns
 
    def take_turn(self):
        if self.num_turns > 0:  #still idle...
            #do nothing
            self.num_turns -= 1
 
        else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer unaware of your presence!', libtcod.red)

class RangedMonster:
    #Ai for ranged monster
    def __init__(self, range=4):
        self.range=range
        
    def take_turn(self):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
 
            #move towards player if far away or away if too close
            if monster.distance_to(player) >= (self.range+1):
                monster.move_towards(player.x, player.y)
 
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
    
 
class Item:
    #an item that can be picked up and used.
    def __init__(self, pickup_line=None, use_function=None, shop_cost=0):
        self.use_function = use_function
        self.pickup_line = pickup_line
        self.shop_cost = shop_cost
 
    def pick_up(self):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            if not self.owner.stackable:
                inventory.append(self.owner)
                objects.remove(self.owner)
                if self.pickup_line == None:
                    message('You picked up a ' + self.owner.name + '!', libtcod.green)
                else:
                    message(self.pickup_line, libtcod.green)
            else:
                self.owner.stackable.pick_up()
 
    def drop(self):
        #special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()
 
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
 
    def use(self):
        #special case: if the object has the Equipment component, the "use" action is to equip/dequip
        if self.owner.equipment:
            print "toggling equip"
            self.owner.equipment.toggle_equip()
            return
        
        #special case: if the item is a spell, cast it
        if self.owner.spell:
            self.owner.spell.cast()
            return
 
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                if not self.owner.stackable:
                    inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                else:
                    self.owner.stackable.spend(inventory)
 
class Equipment:
    #an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, kind=None, type=None, range=TORCH_RADIUS, ranged_damage=0,
                 power_bonus=0, defense_bonus=0, max_hp_bonus=0, max_mp_bonus=0,
                 dodge_bonus=0, crit_chance_bonus=0, crit_dmg_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.max_mp_bonus = max_mp_bonus
        self.dodge_bonus = dodge_bonus
        self.crit_chance_bonus = crit_chance_bonus
        self.crit_dmg_bonus = crit_dmg_bonus
        self.range = range #The range at which a ranged weapon can attack (max is FOV range)
        self.ranged_damage = ranged_damage
 
        self.slot = slot
        self.kind = kind #the kind of weapon (ranged, melee, ...)
        self.type = type #damage or ammo type (blunt, cutting, ... ; bow, crossbow, ...)
        self.is_equipped = False
 
    def toggle_equip(self):  #toggle equip/dequip status
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()
 
    def equip(self):
        global game_state
        print "slot to equip: "+self.slot
        if self.slot != 'left hand' and self.slot != 'right hand' and self.slot != 'both hands': #other
            #if the slot is already being used, dequip whatever is there first
            print "not hands"
            old_equipment = get_equipped_in_slot(self.slot)
            if old_equipment is not None:
                
                print 'dequipping...'
                old_equipment.dequip()
        
        elif self.slot == 'both hands': #2handed
            print "both hands"
            old_equipment = [get_equipped_in_slot('both hands')]
            if old_equipment[0] == None: #No 2 handed equipped, looking further
                old_equipment = [get_equipped_in_slot('left hand')]
                if old_equipment[0] == None: #No left handed weapon
                    old_equipment = [get_equipped_in_slot('right hand')]
                else: #A lefthanded weapon is equipped
                    if get_equipped_in_slot('right hand') != None: #Both hands are full
                        old_equipment.append(get_equipped_in_slot('right hand'))
            print old_equipment
            if old_equipment[0] is not None:
                for thing in old_equipment:
                    thing.dequip()
        
        elif self.slot == 'left hand' or self.slot == 'right hand': #1handed6
            old_equipment = get_equipped_in_slot('both hands')
            if old_equipment == None:
                old_equipment = get_equipped_in_slot(self.slot)
                print 'old = one handed'
            if old_equipment is not None:
                old_equipment.dequip()
                
        #equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
        
        #Enter ranged mode if kind is ranged
        if self.kind == 'ranged':
            print "entering ranged_mode"
            game_state='ranged'
 
    def dequip(self):
        global game_state
        
        #dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
        
        #Leaving ranged mode if previously in it
        if game_state == 'ranged' and self.kind == 'ranged':
            print "leaving ranged mode"
            game_state = 'playing'

class Spell:
    #A spell is put in the spellbook and obtained through books
    def __init__(self, cast, cost, pickup_line=None):
        self.cast = cast
        self.cost = cost
        self.pickup_line = pickup_line
    
    def pick_up(self):
        #add to the player's spellbook and remove from the map
        if len(spellbook) >= 26:
            message('Your spellbook is full, cannot learn ' + self.owner.name + '.', libtcod.red)
        else:
            spellbook.append(self.owner)
            objects.remove(self.owner)
            if self.pickup_line == None:
                message('You learned ' + self.owner.name + '!', libtcod.green)
            else:
                message(self.pickup_line, libtcod.green)
    
    def drop(self):
        #add to the map and remove from the player's spellbook. also, place it at the player's coordinates
        objects.append(self.owner)
        spellbook.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped the page containing ' + self.owner.name + '.', libtcod.yellow)
    
    def use(self):
        print self.cost
        print player.fighter.mp
        if self.cost <= player.fighter.mp:
            self.cast()
            player.fighter.mp -= self.cost
            return True
        else:
            message("You don't have enough mana to cast this", libtcod.red)
            return False

class Stackable:
    #Stackable items can be placed on top of each other and only use 1 inv slot.
    def __init__(self, amount=1):
        self.amount = amount
        
    def pick_up(self):
        #Check if there is already a stack in inv
        found = False
        added = False
        for item in inventory:
            if item.stackable and item.name == self.owner.name and not added: #There is! Now put it on the stack and dispose of yourself!
                item.stackable.amount += self.amount
                objects.remove(self.owner)
                message('You added ' + str(self.amount) + ' units of ' + self.owner.name + ' to your inventory!', libtcod.green)
                found = True
                added=True
        
        if not found: #Create a new stack in inventory
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up ' + str(self.amount) + ' units of ' + self.owner.name + '!', libtcod.green)
    
    def spend(self, container):
        #Spend 1 item from the stack, deleting it if necessary
        print "amount before spend: " + str(self.amount)
        self.amount -= 1
        print "amount after spend: " + str(self.amount)
        if self.amount <= 0:
            print "all gone: removing from: " + str(container)
            if self.owner.equipment and self.owner.equipment.is_equipped:
                self.owner.equipment.dequip()
            container.remove(self.owner)
            if container == inventory:
                message('You used the last of your '+self.owner.name+'.', libtcod.red)
    
    def add(self, container):
        #Adds a new stack to a list or otherwise add to existing stack
        print "checking container for existing stack"
        found = False
        for thing in container:
            if thing.stackable and thing.name == self.owner.name and not found:
                print "found one"
                thing.stackable.amount += 1
                found =True
        
        if not found:
            print "none found, adding new item"
            new_item = Object(self.owner.x, self.owner.y, self.owner.char, self.owner.name, self.owner.color,
                              self.owner.blocks, self.owner.always_visible, item=self.owner.item, stackable=Stackable())
            container.append(new_item)


def create_money(amount, x=0, y=0):
    margin = amount // 10 #floats for now, int at the very end
    act_amount = libtcod.random_get_float(0, max(0, amount - margin), amount + margin)
    stackable_component = Stackable(int(act_amount))
    item_component = Item()
    return Object(x, y, '$', 'money', libtcod.gold, always_visible=True, item=item_component, stackable=stackable_component)
 
def get_equipped_in_slot(slot):  #returns the equipment in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            print obj.name+" in slot: "+slot
            return obj.equipment
    return None

def get_bow():
    for thing in inventory:
        if thing.equipment and thing.equipment.kind=='ranged' and thing.equipment.is_equipped:
            return thing
    return None
 
def get_all_equipped(obj):  #returns a list of equipped items
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return []  #other objects have no equipment
 
 
def is_blocked(x, y):
    #first test the map tile
    if map[x][y].blocked:
        return True
 
    #now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
 
    return False
 
def create_room(room):
    global map
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False
 
def create_h_tunnel(x1, x2, y):
    global map
    #horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def create_v_tunnel(y1, y2, x):
    global map
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def make_map():
    global map, objects, stairs, stair_x, stair_y, merchant
 
    #the list of objects with just the player
    objects = [player]
 
    #fill map with "blocked" tiles
    map = [[ Tile(True) for y in range(MAP_HEIGHT) ] for x in range(MAP_WIDTH) ]
 
    rooms = []
    num_rooms = 0
 
    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
 
        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
 
        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            create_room(new_room)
 
            #add some contents to this room, such as monsters
            place_objects(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_rooms == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel
 
                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()
 
                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
 
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
            
    #Where the stairs are supposed to go:
    stair_x = new_x
    stair_y = new_y
    
    ##Dummy stairs
    stairs = Object(-1, -1, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()  #so it's drawn below the monsters
    
    #Clear the bossroom before creating the boss
    clear_room(rooms[-1])
    
    ##BOSS GOES HERE##
    fighter_component = Fighter(hp=30, defense=3, power=8, xp=150, death_function=boss_death)
    ai_component = BasicMonster()
    boss = Object(new_x, new_y, 'O', 'The Gatekeeper', libtcod.desaturated_green,
                  blocks=True, fighter=fighter_component, ai=ai_component)
    objects.append(boss)
    
    ##CREATE MERCHANT
    create_merchant = True #Add conditions here
    if create_merchant:
        index_found=False
        while not index_found:
            index = libtcod.random_get_int(0, 1, len(rooms)-2)
            if True: #Condition for the room (not already smth else, ...)
                index_found = True
        merch_room = rooms[index]
        clear_room(merch_room)
        (merch_x, merch_y) = merch_room.center()
        merchant = Object(merch_x, merch_y, '@', 'merchant', libtcod.gold, always_visible=True, blocks=True)
        objects.append(merchant)
 
def random_choice_index(chances):  #choose one option from list of chances, returning its index
    #the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))
 
    #go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w
 
        #see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1
 
def random_choice(chances_dict):
    #choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()
 
    return strings[random_choice_index(chances)]
 
def from_dungeon_level(table):
    #returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0
 
def place_objects(room):
    #this is where we decide the chance of each monster or item appearing.
 
    #maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
 
    #chance of each monster
    monster_chances = {}
    monster_chances['orc'] = 80  #orc always shows up, even if all other monsters have 0 chance
    monster_chances['archer'] = 10
    monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
 
    #maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])
 
    #chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    
    #Potions
    item_chances['heal'] = 35  #healing potion always shows up, even if all other items have 0 chance
    item_chances['restore'] = 5
    
    #Scrolls
    item_chances['lightning'] =     from_dungeon_level([[25, 4]])
    item_chances['fireball'] =      from_dungeon_level([[25, 6]])
    item_chances['confuse'] =       from_dungeon_level([[10, 2]])
    
    #Held
    item_chances['sword'] =         from_dungeon_level([[5, 1], [10, 3], [15, 5]])
    item_chances['shield'] =        from_dungeon_level([[15, 3]])
    
    #Low-tier armor
    item_chances['boots'] =         from_dungeon_level([[5, 1], [0, 5]])
    item_chances['pants'] =         from_dungeon_level([[5, 1], [0, 5]]) # Either someone got split in half or found the amplify elasticity spell. #TROLL_RAPE
    item_chances['shirt'] =         from_dungeon_level([[5, 1], [0, 5]]) # #VeiligOpCafe
    
    #'High'-tier armor
    item_chances['helmet'] =        from_dungeon_level([[10, 4], [15, 6]])
    item_chances['chainmail'] =     from_dungeon_level([[5, 5], [10, 8]])
    item_chances['platelegs'] =     from_dungeon_level([[5, 5], [10, 8]])
    
    #Spells
    item_chances['fireball_book'] = from_dungeon_level([[5, 2]])
    
    
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'orc':
                #create an orc
                fighter_component = Fighter(hp=20, defense=0, power=4, xp=35, money_amount=50, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks=True, fighter=fighter_component, ai=ai_component)
            
            elif choice == 'archer':
                #create an undead archer
                fighter_component = Fighter(hp=15, defense=0, power=3, xp=35, money_amount=40, death_function=monster_death)
                ai_component = RangedMonster()
                monster = Object(x, y, '0', 'undead archer', libtcod.desaturated_green, blocks=True, fighter=fighter_component, ai=ai_component)
 
            elif choice == 'troll':
                #create a troll
                fighter_component = Fighter(hp=30, defense=2, power=8, xp=100, money_amount=150, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks=True, fighter=fighter_component, ai=ai_component)

            objects.append(monster)
 
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            
            #Potions
            if choice == 'heal':
                #create a healing potion
                item_component = Item(use_function=heal_40)
                stackable_component = Stackable()
                item_name = String.heal_string()
                item = Object(x, y, '!', item_name, libtcod.red, item=item_component, stackable=stackable_component)
            
            if choice == 'restore':
                #create a healing potion
                item_component = Item(use_function=restore_40)
                stackable_component = Stackable()
                item = Object(x, y, '!', 'mana potion', libtcod.blue, item=item_component, stackable=stackable_component)
            
            #Scrolls
            elif choice == 'lightning':
                #create a lightning bolt scroll
                item_component = Item(use_function=cast_lightning)
                stackable_component = Stackable()
                item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component, stackable=stackable_component)
 
            elif choice == 'fireball':
                #create a fireball scroll
                item_component = Item(use_function=cast_fireball)
                stackable_component = Stackable()
                item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component, stackable=stackable_component)
 
            elif choice == 'confuse':
                #create a confuse scroll
                item_component = Item(use_function=cast_confuse)
                stackable_component = Stackable()
                item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component, stackable=stackable_component)

            #equipment (held)
            elif choice == 'sword':
                #create a sword
                equipment_component = Equipment(slot='right hand', power_bonus=2)
                item = Object(x, y, '/', 'sword', libtcod.sky, equipment=equipment_component)
 
            elif choice == 'shield':
                #create a shield
                equipment_component = Equipment(slot='left hand', defense_bonus=2)
                item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
            
            #Low-tier armor
            elif choice == 'boots':
                #create a helmet
                item_component = Item(pickup_line='Did someone drop his shoe?')
                equipment_component = Equipment(slot='feet', dodge_bonus=4)
                item = Object(x, y, '~', 'boots', libtcod.darker_green, equipment=equipment_component, item=item_component)
            
            elif choice == 'pants':
                #create pants
                equipment_component = Equipment(slot='legs', max_hp_bonus=10)
                item = Object(x, y, '=', 'pants', libtcod.darker_green, equipment=equipment_component)
            
            elif choice == 'shirt':
                #create a shirt
                equipment_component = Equipment(slot='torso', defense_bonus=1)
                item = Object(x, y, 'H', 'shirt', libtcod.darker_green, equipment=equipment_component)
            
            #High-tier armor
            elif choice == 'helmet':
                #create a helmet
                equipment_component = Equipment(slot='head', defense_bonus=1)
                item = Object(x, y, '^', 'helmet', libtcod.darker_cyan, equipment=equipment_component)
            
            elif choice == 'chainmail':
                #create a helmet
                equipment_component = Equipment(slot='torso', defense_bonus=3)
                item = Object(x, y, 'H', 'chainmail', libtcod.darker_cyan, equipment=equipment_component)
            
            elif choice == 'platelegs':
                #create a helmet
                equipment_component = Equipment(slot='legs', max_hp_bonus=25)
                item = Object(x, y, '=', 'platelegs', libtcod.darker_cyan, equipment=equipment_component)
            
            elif choice == 'fireball_book':
                #create a book containing fireball
                spell_component = Spell(cast=cast_fireball, cost=80, pickup_line='Danger: highly explosive')
                item = Object(x, y, 'B', 'fireball', libtcod.darker_red, spell=spell_component)
 
            objects.append(item)
            item.send_to_back()  #items appear below other objects
            item.always_visible = True  #items are visible even out-of-FOV, if in an explored area
 

def get_objects(x,y):
    output = []
    for thing in objects:
        if thing.x==x and thing.y==y:
            output.append(thing)
    return output

def clear_room(room):
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            contents = get_objects(x,y)
            if not len(contents)==0:
                for thing in contents:
                    objects.remove(thing)
            

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
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                                 name + ': ' + str(value) + '/' + str(maximum))
 
def get_names_under_mouse():
    global mouse
    #return a string with the names of all objects under the mouse
 
    (x, y) = (mouse.cx, mouse.cy)
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.full_name for obj in objects
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
 
        #go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:
                    #if it's not visible right now, the player can only see it if it's explored
                    if map[x][y].explored:
                        if wall:
                            libtcod.console_put_char_ex(con, x, y, '#', color_dark_wall, libtcod.black)
                        else:
                            libtcod.console_put_char_ex(con, x, y, '.', color_dark_ground, libtcod.black)
                else:
                    #it's visible
                    if wall:
                        libtcod.console_put_char_ex(con, x, y, '#', color_light_wall, libtcod.black)
                    else:
                        libtcod.console_put_char_ex(con, x, y, '.', color_light_ground, libtcod.black)
                        #since it's visible, explore it
                    map[x][y].explored = True
 
    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for object in objects:
        if object != player:
            object.draw()
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
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT,line)
        y += 1
 
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
               libtcod.light_red, libtcod.darker_red) #Health
    
    render_bar(1, 2, BAR_WIDTH, 'MP', player.fighter.mp, player.fighter.max_mp,
               libtcod.light_blue, libtcod.darker_blue) #MP
    
    render_bar(1, 3, BAR_WIDTH, 'XP', player.fighter.xp, get_xp(player.level),
               libtcod.light_orange, libtcod.darker_orange) #XP
    
    libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Player level ' + str(player.level))
    libtcod.console_print_ex(panel, 1, 6, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(dungeon_level))
 
    #display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
 
 
def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )
 
 
def player_move_or_attack(dx, dy):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
 
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
        return True
    elif not is_blocked(x,y):
        player.move(dx, dy)
        #Finding money or other to pickup
        for object in objects:
            if object.name == 'money' and object.x==player.x and object.y==player.y:
                object.item.pick_up()
        fov_recompute = True
        return True
    elif (x, y) == (merchant.x, merchant.y):
        message(String.npc_bump())
        return False
    else:
        message(String.wall_bump())
        return False
 
 
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
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)
 
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
            text = item.name
            #show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            #if it's a stackable
            if item.stackable:
                text = text + ' (' + str(item.stackable.amount) + ')'
            options.append(text)
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index]

def spellbook_menu(header):
    #show a menu with each item of the spellbook as an option
    if len(spellbook) == 0:
        options = ['Spellbook is empty.']
    else:
        options = []
        for spell in spellbook:
            text = spell.name + ' (costs ' + str(spell.spell.cost) + ')'
            options.append(text)
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if a spell was chosen, return it
    if index is None or len(spellbook) == 0: return None
    return spellbook[index].spell

def shop_menu(header):
    if len(catalog) == 0:
        options = ['The shop is empty.']
    else:
        options = []
        for thing in catalog:
            adding = ''
            if thing.stackable:
                adding = ' (' + str(thing.stackable.amount) + ')'
            text = thing.name + adding + ' costs ' + str(thing.item.shop_cost) + ' munnies.'
            options.append(text)
    
    index = menu(header, options, INVENTORY_WIDTH)
    
    if index is None or len(catalog) == 0: return None
    cost = catalog[index].item.shop_cost
    item = catalog[index]
    if cost <= get_player_money():
        spend_player_money(cost)
        return item
    else:
        message("You don't have enough money to buy this item.", libtcod.red)

def shop_sell_menu(header):
    #show a menu with each item of the inventory as an option and its selling price
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            if not item.name == 'money':
                text = item.name
                #if it's a stackable
                if item.stackable:
                    text = text + ' (' + str(item.stackable.amount) + ')'
                #The selling price
                text = text + ' sells for ' + str(item.item.shop_cost/2)
                options.append(text)
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory_without_money()[index]

def inventory_without_money():
    new_inventory = []
    for item in inventory:
        if item.name != 'money':
            new_inventory.append(item)
    return new_inventory

def get_player_money():
    for thing in inventory:
        if thing.name == 'money':
            return thing.stackable.amount
    return 0

def spend_player_money(amount):
    for thing in inventory:
        if thing.name == 'money':
            assert thing.stackable.amount >= amount
            thing.stackable.amount -= amount
 
def msgbox(text, width=50):
    menu(text, [], width)  #use menu() as a sort of "message box"
 
def handle_keys():
    global key
 
    if key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game
 
    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
            if not player_move_or_attack(0, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
            if not player_move_or_attack(0, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
            if not player_move_or_attack(-1, 0):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
            if not player_move_or_attack(1, 0):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7:
            if not player_move_or_attack(-1, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9:
            if not player_move_or_attack(1, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1:
            if not player_move_or_attack(-1, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3:
            if not player_move_or_attack(1, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_KP5:
            pass  #do nothing ie wait for the monster to come to you
        else:
            #test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                #pick up an item
                for thing in objects:  #look for an item in the player's tile
                    if thing.x == player.x and thing.y == player.y and (thing.item or thing.spell):
                        if thing.item:
                            thing.item.pick_up()
                        elif thing.spell:
                            thing.spell.pick_up()
                        break

            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.item.use()

            if key_char == 's':
                #show the spellbook; if a spell is selected, cast it
                chosen_item = spellbook_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    if chosen_item.use():
                        render_all()
                        return

            if key_char == 'd':
                #show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.item.drop()

            if key_char == 'c':
                #show character information
                msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                       '\nExperience to level up: ' + str(get_xp(player.level)) +
                       '\n\nMaximum HP: ' + str(player.fighter.base_max_hp) + ' (' + str(player.fighter.max_hp) +
                       ')\nAttack: ' + str(player.fighter.base_power) + ' (' + str(player.fighter.power) +
                       ')\nDefense: ' + str(player.fighter.base_defense) + ' (' + str(player.fighter.defense) +
                       ')\nDodge chance: ' + str(player.fighter.dodge) + ' (' + str(player.fighter.dodge) + ')'
                       , CHARACTER_SCREEN_WIDTH)

            if key_char == '<':
                #go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()

            if key.vk == libtcod.KEY_KP0:
                #Do all the things (pickup items/go down stairs)
                
                #pick up an item
                for thing in objects:  #look for an item in the player's tile
                    if thing.x == player.x and thing.y == player.y and (thing.item or thing.spell):
                        if thing.item:
                            thing.item.pick_up()
                        elif thing.spell:
                            thing.spell.pick_up()
                
                #go down stairs, if the player is on them. You can deal with your picked up items when you get there
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()

            if key_char == 'k': #Kopen
                #Check if near shop and buy things
                print 'checking for shops'
                if (-1 <= player.x-merchant.x <= 1) and (-1 <= player.y-merchant.y <= 1):
                    print 'shopping'
                    chosen_item = shop_menu('Welcome to my humble shop...')
                    if chosen_item != None:
                        if not chosen_item.stackable:
                            catalog.remove(chosen_item)
                            objects.append(chosen_item)
                        else:
                            catalog[catalog.index(chosen_item)].stackable.spend(catalog)
                            new_item=Object(chosen_item.x, chosen_item.y, chosen_item.char, chosen_item.name, chosen_item.color,
                                            always_visible=True, item=chosen_item.item, stackable=Stackable())
                            chosen_item = new_item
                            objects.append(chosen_item)
                        message('The merchant threw the ' + chosen_item.name + ' at your feet.', libtcod.gold)
                        chosen_item.item.pick_up()

            if key_char == 'v': #Verkopen
                #Check if near shop and sell things
                if (-1 <= player.x-merchant.x <= 1) and (-1 <= player.y-merchant.y <= 1):
                    print 'selling'
                    chosen_item = shop_sell_menu('Select an item to sell.')
                    if chosen_item != None:
                        spend_player_money(-chosen_item.item.shop_cost/2)
                        if chosen_item.stackable:
                            chosen_item.stackable.add(catalog)
                            chosen_item.stackable.spend(inventory)
                            message('The shopkeeper accepted the item', libtcod.gold)
                        else:
                            chosen_item.item.drop()
                            objects.remove(chosen_item)
                            catalog.append(chosen_item)
                            message('and the shopkeeper picked it up', libtcod.gold)
            
            return 'didnt-take-turn'

def handle_ranged_keys():
    global key, mouse
    (x, y) = (mouse.cx, mouse.cy)
    
    if key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game
    
    if game_state == 'ranged': #Making sure you're not dead
        #movement keys
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
            if not player_move_or_attack(0, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
            if not player_move_or_attack(0, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
            if not player_move_or_attack(-1, 0):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
            if not player_move_or_attack(1, 0):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7:
            if not player_move_or_attack(-1, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9:
            if not player_move_or_attack(1, -1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1:
            if not player_move_or_attack(-1, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3:
            if not player_move_or_attack(1, 1):
                return 'didnt-take-turn'
        elif key.vk == libtcod.KEY_KP5:
            pass  #do nothing ie wait for the monster to come to you
        elif (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
                    (player.distance(x, y) <= get_bow().equipment.range)):
            print 'shooting ('+str(x)+','+str(y)+')...'
            if not shoot(x,y): #Shoot @ target tile w/ equipped arrows through equipped ranged weapon
                return 'didnt-take-turn'
        
        else:
            #Check for keys that don't take turns
            key_char = chr(key.c)
            
            if key_char == 'g':
                #pick up an item
                for thing in objects:  #look for an item in the player's tile
                    if thing.x == player.x and thing.y == player.y and (thing.item or thing.spell):
                        if thing.item:
                            thing.item.pick_up()
                        elif thing.spell:
                            thing.spell.pick_up()
                        break
        
            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.item.use()
            
            if key_char == 's':
                #show the spellbook; if a spell is selected, cast it
                chosen_item = spellbook_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    if chosen_item.use():
                        render_all()
                        return
        
            if key_char == 'd':
                #show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.item.drop()
        
            if key_char == 'c':
                #show character information
                msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                       '\nExperience to level up: ' + str(get_xp(player.level)) +
                       '\n\nMaximum HP: ' + str(player.fighter.base_max_hp) + ' (' + str(player.fighter.max_hp) +
                       ')\nAttack: ' + str(player.fighter.base_power) + ' (' + str(player.fighter.power) +
                       ')\nDefense: ' + str(player.fighter.base_defense) + ' (' + str(player.fighter.defense) +
                       ')\nDodge chance: ' + str(player.fighter.dodge) + ' (' + str(player.fighter.dodge) + ')'
                       , CHARACTER_SCREEN_WIDTH)
        
            if key_char == '<':
                #go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
        
            if key.vk == libtcod.KEY_KP0:
                #Do all the things (pickup items/go down stairs)
                
                #pick up an item
                for thing in objects:  #look for an item in the player's tile
                    if thing.x == player.x and thing.y == player.y and (thing.item or thing.spell):
                        if thing.item:
                            thing.item.pick_up()
                        elif thing.spell:
                            thing.spell.pick_up()
                
                #go down stairs, if the player is on them. You can deal with your picked up items when you get there
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
        
            if key_char == 'k': #Kopen
                #Check if near shop and buy things
                print 'checking for shops'
                if (-1 <= player.x-merchant.x <= 1) and (-1 <= player.y-merchant.y <= 1):
                    print 'shopping'
                    chosen_item = shop_menu('Welcome to my humble shop...')
                    if chosen_item != None:
                        if not chosen_item.stackable:
                            catalog.remove(chosen_item)
                            objects.append(chosen_item)
                        else:
                            catalog[catalog.index(chosen_item)].stackable.spend(catalog)
                            new_item=Object(chosen_item.x, chosen_item.y, chosen_item.char, chosen_item.name, chosen_item.color,
                                            always_visible=True, item=chosen_item.item, stackable=Stackable())
                            chosen_item = new_item
                            objects.append(chosen_item)
                        message('The merchant threw the ' + chosen_item.name + ' at your feet.', libtcod.gold)
                        chosen_item.item.pick_up()
        
            if key_char == 'v': #Verkopen
                #Check if near shop and sell things
                if (-1 <= player.x-merchant.x <= 1) and (-1 <= player.y-merchant.y <= 1):
                    print 'selling'
                    chosen_item = shop_sell_menu('Select an item to sell.')
                    if chosen_item != None:
                        spend_player_money(-chosen_item.item.shop_cost/2)
                        if chosen_item.stackable:
                            chosen_item.stackable.add(catalog)
                            chosen_item.stackable.spend(inventory)
                            message('The shopkeeper accepted the item', libtcod.gold)
                        else:
                            chosen_item.item.drop()
                            objects.remove(chosen_item)
                            catalog.append(chosen_item)
                            message('and the shopkeeper picked it up', libtcod.gold)
            
            return 'didnt-take-turn'

def get_xp(level):
    if level > 0:
        return LEVEL_UP_BASE + level*LEVEL_UP_FACTOR
    else:
        return 0
 
def check_level_up():
    #see if the player's experience is enough to level-up
    level_up_xp = get_xp(player.level)
    if player.fighter.xp >= level_up_xp:
        #it is! level up and ask to raise some stats
        player.level += 1
        player.fighter.xp -= level_up_xp
        message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
 
        choice = None
        while choice == None:  #keep asking until a choice is made
            choice = menu('Level up! Choose a stat to raise:\n',
                          ['Constitution (+20 HP, from ' + str(player.fighter.base_max_hp) + ')',
                           'Intelligence (+20 MP, from ' + str(player.fighter.base_max_mp) + ')',
                           'Strength (+1 attack, from ' + str(player.fighter.base_power) + ')',
                           'Fortitude (+1 defense, from ' + str(player.fighter.base_defense) + ')',
                           'Agility (+2 dodge chance, from ' + str(player.fighter.base_dodge) + ')'], LEVEL_SCREEN_WIDTH)
 
        if choice == 0:
            player.fighter.base_max_hp += 20
            player.fighter.hp += 20
        elif choice == 1:
            player.fighter.base_max_mp += 20
            player.fighter.mp += 20    
        elif choice == 2:
            player.fighter.base_power += 1
        elif choice == 3:
            player.fighter.base_defense += 1
        elif choice == 4:
            player.fighter.base_dodge += 2
 
def player_death(player):
    #the game ended!
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'
 
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
 
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    drop = create_money(monster.fighter.money_amount, monster.x, monster.y)
    objects.append(drop)
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()

def boss_death(boss):
    global stairs, stair_x, stair_y
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(boss.name + ' is dead! You gain ' + str(boss.fighter.xp) + ' experience points.', libtcod.orange)
    boss.char = '%'
    boss.color = libtcod.dark_red
    boss.blocks = False
    boss.fighter = None
    boss.ai = None
    boss.name = 'remains of ' + boss.name
    boss.send_to_back()
    #create stairs at the center of the last room
    #DEBUG# print "creating stairs on: ("+str(stair_x)+","+str(stair_y)+")"
    stairs = Object(stair_x, stair_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()  #so it's drawn below the monsters
 
def target_tile(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
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
 
    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


# Many healing amounts for many healing tiers
def heal_40():
    return cast_heal(40)

def cast_heal(amount):
    #heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'
 
    message('Your wounds start to feel better!', libtcod.light_violet)
    player.fighter.heal(amount)

#Many restoring amounts for many restoring tiers
def restore_40():
    return cast_restore(40)
    

def cast_restore(amount):
    #Restore MP
    if player.fighter.mp == player.fighter.max_mp:
        message('You are already at full MP.', libtcod.red)
        return 'cancelled'
 
    message('Your mind starts to become clearer!', libtcod.light_violet)
    player.fighter.restore(amount)
 
def cast_lightning():
    #find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None:  #no enemy found within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'
 
    #zap it!
    message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
            + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)
 
def cast_fireball():
    #ask the player for a target tile to throw a fireball at
    message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
 
    for obj in objects:  #damage every fighter in range, including the player
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(FIREBALL_DAMAGE)
 
def cast_confuse():
    #ask the player for a target to confuse
    message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None: return 'cancelled'
 
    #replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster  #tell the new component who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)

def magic_missile():
    return cast_strike(20)

def cast_strike(damage):
    #ask the player for a target to strike
    message('Left-click an enemy to hit it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None: return 'cancelled'
    
    message('The ' + monster.name + ' gets hit for ' + str(damage) + ' hit points.', libtcod.orange)
    monster.fighter.take_damage(damage)

def shoot(x, y):
    weapon = get_bow()
    if weapon == None or (not weapon.equipment) or (not weapon.equipment.kind == 'ranged'):
        #You shouldn't get here
        print "something is wrong, in ranged mode without ranged weapon :("
        message('No ranged weapon equipped!', libtcod.red)
        return False
    
    #We are now sure we have a ranged weapon.
    #We now make sure we have ammo and if so: spend 1 ammo and get damage
    if weapon.equipment.type == None:
        #We have a self-containing ranged weapon (ping pong balls or smth)
        #THESE HAVE TO BE STACKABLE!!
        damage = weapon.equipment.ranged_damage
        weapon.stackable.spend(inventory) #Dequips if necessary thus leaving ranged mode
        #                                 #This also ensures we always have ammo if the weapon is stackable
    elif (type(weapon.equipment.type)==list and weapon.equipment.type[0]=='mana'): #Checking for mana-based item
        #Checking for sufficient mana
        mana_amount = weapon.equipment.type[1]
        if (player.fighter.mp < mana_amount):
            message("You don't have enough mana to cast this!", libtcod.red)
            return False
        damage = weapon.equipment.ranged_damage
        player.fighter.mp -= mana_amount
    else:
        #Checking for viable ammo:
        ammo = get_equipped_in_slot('quiver')
        if (ammo == None):
            message("There's nothing in your quiver to shoot!", libtcod.red)
            return False
        elif (ammo.type != weapon.equipment.type):
            message("This isn't the right ammo for this weapon!", libtcod.red)
            return False
        damage = ammo.ranged_damage + weapon.equipment.ranged_damage
        ammo.owner.stackable.spend(inventory)
        
    for obj in objects:
        if obj.x == x and obj.y == y and obj.fighter and obj != player:
            message('you shoot the ' + obj.name + ' and he gets hit for ' + str(damage) + ' hit points.')
            obj.fighter.take_damage(damage)
            return True
    message('You hit nothing... Great job!')
    return True
 
def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index'] = objects.index(player)  #index of player in objects list
    file['merchant_index'] = objects.index(merchant)
    file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['inventory'] = inventory
    file['spellbook'] = spellbook
    file['catalog'] = catalog
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    file['dungeon_level'] = dungeon_level
    file.close()
 
def load_game():
    #open the previously saved shelve and load the game data
    global map, objects, player, merchant, stairs, inventory, catalog, spellbook, game_msgs, game_state, dungeon_level
 
    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]  #get index of player in objects list and access it
    merchant = objects[file['merchant_index']] #same for the merchant
    stairs = objects[file['stairs_index']]  #and for the stairs
    inventory = file['inventory']
    spellbook = file['spellbook']
    catalog = file['catalog']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    dungeon_level = file['dungeon_level']
    file.close()
 
    initialize_fov()
 
def new_game():
    global player, inventory, spellbook, catalog, game_msgs, game_state, dungeon_level
    
    img = libtcod.image_load('menu_background.png')
    
    time.sleep(0.5)
    
    #Choose name here
    libtcod.image_blit_2x(img, 0, 0, 0)
    name_chosen = False
    while not name_chosen:
        name_choice = menu('Choose a name', PLAYER_NAMES, 24)
        if 0<=name_choice<len(PLAYER_NAMES):
            name_chosen = True
    player_name = PLAYER_NAMES[name_choice]
    
    time.sleep(0.5) #Waiting for frames to pass
    
    #Choose class here
    libtcod.image_blit_2x(img, 0, 0, 0)
    class_chosen = False
    while not class_chosen:  #keep asking until a class_choice is made
        class_choice = menu('Choose a class', CLASSES, 24)
        if 0<=class_choice<len(CLASSES):
            class_chosen = True

    inventory=[]
    #init class specific traits/equipment
    class_inventory = []
    class_spells = []
    class_hp = None
    class_defense = None
    class_power = None
    class_mp = None
    class_dodge = None
    class_crit_chance = None
    class_crit_dmg = None

    if class_choice == 0: #Goku
        class_inventory = []
        class_spells = []
        item_component = Item(shop_cost=500)
        equipment_component1 = Equipment(slot='right hand', power_bonus=3)
        obj1 = Object(0, 0, 'P', "'djoef op uw mulle'-hamer", libtcod.sky, equipment=equipment_component1, item=item_component)
        inventory.append(obj1)
        class_inventory.append(obj1)
        equipment_component2 = Equipment(slot='wrists', power_bonus=3)
        obj2 = Object(0, 0, '8', 'burlesque handschoenen', libtcod.red, equipment=equipment_component2)
        inventory.append(obj2)
        class_inventory.append(obj2)
        class_hp = 120
        class_defense = 3
        class_power = 6
        class_mp = 60
        class_dodge = 10
        class_crit_chance = 8
        class_crit_dmg = 150
        player_class_name='Super Saiyan 3'
    
    elif class_choice == 1: #Toverknol
        class_inventory = []
        class_spells = []
        equipment_component1 = Equipment(slot='right hand', kind='ranged', type=['mana', 20], ranged_damage=20)
        obj1 = Object(0, 0, '?', 'wand of knalboom', libtcod.sky, always_visible = True, equipment=equipment_component1)
        equipment_component2 = Equipment(slot='torso', max_hp_bonus=20)
        obj2 = Object(0, 0, 'V', 'maagdelijk witte tuniek', libtcod.white, always_visible = True, equipment=equipment_component2)
        equipment_component3 = Equipment(slot='left hand', kind='melee', power_bonus=2, max_mp_bonus=20)
        obj3 = Object(0, 0, 'j', 'knollenstok', libtcod.sky, always_visible = True, equipment=equipment_component3)
        inventory.append(obj1)
        class_inventory.append(obj1)
        inventory.append(obj2)
        class_inventory.append(obj2)
        inventory.append(obj3)
        class_inventory.append(obj3)
        class_hp = 80
        class_defense = 1
        class_power = 2
        class_mp = 150
        class_dodge = 12
        class_crit_chance = 8
        class_crit_dmg = 125
        player_class_name='toverknol'
    
    elif class_choice == 2: #Pikkendief
        class_inventory = []
        class_spells = []
        equipment_component1 = Equipment(slot='right hand', power_bonus=1)
        obj1 = Object(0, 0, '-', 'roestig mes', libtcod.copper, always_visible = True, equipment=equipment_component1)
        inventory.append(obj1)
        class_inventory.append(obj1)
        equipment_component2 = Equipment(slot='back', dodge_bonus=3)
        obj2 = Object(0, 0, '#', 'cloaka the cloak', libtcod.grey, always_visible = True, equipment=equipment_component2)
        inventory.append(obj2)
        class_inventory.append(obj2)
        class_hp = 100
        class_defense = 2
        class_power = 5
        class_mp = 70
        class_dodge = 15
        class_crit_chance = 15
        class_crit_dmg = 200
        player_class_name='pikkendief'
    
    elif class_choice == 3: #Paardenridder
        class_inventory = []
        class_spells = []
        equipment_component1 = Equipment(slot='right hand', power_bonus=1)
        obj1 = Object(0, 0, '|', 'spies', libtcod.sky, always_visible = True, equipment=equipment_component1)
        inventory.append(obj1)
        class_inventory.append(obj1)
        equipment_component2 = Equipment(slot='left hand', defense_bonus=1)
        obj2 = Object(0, 0, 'o', 'zeer rond schild', libtcod.sky, always_visible = True, equipment=equipment_component2)
        inventory.append(obj2)
        class_inventory.append(obj2)
        class_hp = 150
        class_defense = 4
        class_power = 4
        class_mp = 50
        class_dodge = 8
        class_crit_chance = 8
        class_crit_dmg = 150
        player_class_name='paardenridder'
    
    elif class_choice == 4: #Boogschutter
        class_inventory = []
        class_spells = []
        equipment_component1 = Equipment(slot='right hand', power_bonus=1)
        obj1 = Object(0, 0, '-', 'scherp mes', libtcod.copper, always_visible = True, equipment=equipment_component1)
        equipment_component2 = Equipment(slot='head', dodge_bonus=3)
        obj2 = Object(0, 0, '^', 'leren kap', libtcod.grey, always_visible = True, equipment=equipment_component2)
        equipment_component3 = Equipment(slot='both hands', kind='ranged', type='arrow', ranged_damage=5)
        obj3 = Object(0, 0, ')', 'plastieken boog', libtcod.sky, always_visible = True, equipment=equipment_component3)
        equipment_component4 = Equipment(slot='quiver', type='arrow', ranged_damage=1)
        obj4 = Object(0, 0, 'l', 'plastieken pijl', libtcod.sky, always_visible=True, equipment=equipment_component4, stackable=Stackable(20))
        inventory.append(obj1)
        class_inventory.append(obj1)
        inventory.append(obj2)
        class_inventory.append(obj2)
        inventory.append(obj3)
        inventory.append(obj4)
        class_inventory.append(obj4)
        class_hp = 100
        class_defense = 2
        class_power = 5
        class_mp = 70
        class_dodge = 10
        class_crit_chance = 10
        class_crit_dmg = 150
        player_class_name='boogschutter'
    
    elif class_choice == 5: #Sterrenkundige, ooooh... Bad choice
        class_inventory = []
        class_spells = []
        equipment_component = Equipment(slot='both hands')
        obj = Object(0, 0, '|', 'telescoop', libtcod.sky, always_visible = True, equipment=equipment_component)
        inventory.append(obj)
        class_inventory.append(obj)
        class_hp = 10
        class_defense = 0
        class_power = 0
        class_mp = 1000
        class_dodge = 0
        class_crit_chance = 0
        class_crit_dmg = 100
        player_class_name='gepeepene'
    
    #create object representing the player
    fighter_component = Fighter(hp=class_hp, defense=class_defense, power=class_power, xp=0, mp=class_mp, dodge=class_dodge,
                                crit_chance=class_crit_chance, crit_dmg=class_crit_dmg, death_function=player_death, player_class=player_class_name)
    player = Object(0, 0, '@', player_name, libtcod.white, blocks=True, fighter=fighter_component)
 
    player.level = 1
 
    #generate map (at this point it's not drawn to the screen)
    dungeon_level = 1
    make_map()
    initialize_fov()
 
    game_state = 'playing'
    spellbook = []
    catalog = []
 
    #create the list of game messages and their colors, starts empty
    game_msgs = []
 
    #a warm welcoming message!
    message('Vuile Baeyens! Taste my blade!!', libtcod.red)
    
    for thing in class_inventory:
        if thing.equipment:
            thing.equipment.equip()
    
    for spell in class_spells:
        spellbook.append(spell)

# Return a list of items to sell at the shop, dependant on current floor and chance.
# Possible also player level, ...
def get_shop_items():
    return []


def next_level():
    #advance to the next level
    global dungeon_level, catalog
    global color_light_wall, color_light_floor, color_dark_wall, color_dark_floor
    message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2)  #heal the player by 50%

    dungeon_level += 1
    catalog = get_shop_items()
    message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
    
    # Do floor dependent stuff here, like changing color layout
    if dungeon_level == 3: #Level 3: jungle
        message("Wow, didn't know plants could grow down here!", libtcod.green)
        color_light_floor = libtcod.darker_lime
        color_light_wall = libtcod.darker_green
    
    make_map()  #create a fresh new level!
    initialize_fov()
 
def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True
 
    #create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
 
    libtcod.console_clear(con)  #unexplored areas start black (which is the default background color)
 
def  play_game():
    global key, mouse, game_state
 
    player_action = None
 
    mouse = libtcod.Mouse()
    key = libtcod.Key()
    #main loop
    while not libtcod.console_is_window_closed():
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        
        #render the screen
        render_all()

        libtcod.console_flush()
 
        #level up if needed
        check_level_up()
 
        #erase all objects at their old locations, before they move
        for object in objects:
            object.clear()
        
        if game_state == 'playing':
            #handle keys and exit game if needed
            player_action = handle_keys()
            if player_action == 'exit':
                save_game()
                break
        
        else:
            #Handle ranged combat and return to normal if necessary
            player_action = handle_ranged_keys()
            if player_action == 'exit':
                save_game()
                break
            elif player_action=='leave':
                game_state = 'playing'
                player_action = 'didnt-take-turn'
 
        #let monsters take their turn
        if (game_state == 'playing' or game_state == 'ranged') and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()
 
def main_menu():
    img = libtcod.image_load('menu_background.png')
 
    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)
 
        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.light_yellow)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
                                 "robins grosse abenteuer")
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER, 'By Xenoxinius and Melinator95')
 
        #show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
 
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

def Start():
    global con, panel
    libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
    libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, String.title_string(), False) #For some terrarian window titles, insert random txt here
    libtcod.sys_set_fps(LIMIT_FPS)
    con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
    panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
     
    main_menu()

Start()