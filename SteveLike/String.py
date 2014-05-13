# Random string choosers, to keep big data away from main_script

import random

TITLE_STRINGS=['Robins grosse abenteuer', 'Caution, small pieces. Keep away from children'] # Strings for window title #Terraria
def title_string():
    index = random.randint(0, len(TITLE_STRINGS)-1)
    return TITLE_STRINGS[index]

HEAL_STRINGS=['schel hesp', 'schel kaas', 'smartie', 'ui', 'ajuin'] # Names for healing items
def heal_string():
    index = random.randint(0, len(HEAL_STRINGS)-1)
    return HEAL_STRINGS[index]

NPC_BUMP_STRINGS=['Dude, watch it!', 'bump!', 'bamp', 'bumpity', 'ouch!'] # When bumping against npc
def npc_bump():
    index = random.randint(0, len(NPC_BUMP_STRINGS)-1)
    return NPC_BUMP_STRINGS[index]

WALL_BUMP_STRINGS=['Wall, watch it!', 'bump!', 'bamp', 'bumpity', 'ouch!', 'You found a hidden path, but you decided to ignore it.'] # When bumping against wall
def wall_bump():
    index = random.randint(0, len(WALL_BUMP_STRINGS)-1)
    return WALL_BUMP_STRINGS[index]