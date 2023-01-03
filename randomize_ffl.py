import random
import time
import pathlib
import csv
import sys
import enum
import math

VERSION = "0.016"

# contact: eclipseyy@gmx.com

# option definitions (bools)
MUTANT_ABILITIES = 0
ARMOR = 1
COMBAT_ITEMS = 2
CHARACTER_ITEMS = 3
ENEMY_ITEMS = 4
SHOPS = 5
CHESTS = 6
MONSTERS = 7
ENCOUNTERS = 8
GUILD_MONSTERS = 9
HP_TABLE = 10
MUTANT_RACE = 11
MEAT = 12
PATCH = 13
TOWER = 14
DUNGEONS = 15
SKYSCRAPER = 16
SMALL_PICS = 17
WORLD_MAPS = 18
DUNGEON_MAPS = 19
TOWER_MAPS = 20

# option definitions (numbers)
TRANSFORMATION_LEVEL_ADJUST = 101
ENCOUNTER_LEVEL_ADJUST = 102
MONSTER_GOLD_OFFSET_ADJUST = 103
GOLD_TABLE_AMOUNT_MULTIPLIER = 104

# shop data, stored in separate index-linked lists
equipment_shop_addrs = [0x17d38, 0x17d4c, 0x17d60, 0x17d74, 0x17d88, 0x17d9c, 0x17db0, 0x17dc4, 0x17dd8, 0x17dec, 0x17e00, 0x17d7e, 0x17dba, 0x17de2]
shop_min_costs = [12, 12, 80, 100, 500, 500, 2060, 4000, 5000, 24, 8000, 500, 500, 500]
shop_max_costs = [500, 1100, 1000, 2500, 9880, 10712, 10712, 32000, 100000, 500, 100000, 15100, 50000, 4100]
shop_contains_battle_sword = [False, False, True, True, False, False, False, False, False, False, False, False, False, False]
shop_equipment_start_idx = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7]

# chest data, stored in separate index-linked lists
# (includes non-story items awarded during speech, like REVENGE and N.BOMB)
chest_addrs = [0xa404, 0xa429, 0xa44e, 0xa47c, 0xa4bf, 0xa4c8, 0xa4d1, 0xa4da, 0xa4e3, 0xa4ec, 0xa4f3, \
         0xa4fa, 0xa501, 0xa513, 0xa53b, 0xa544, 0xa5d7, 0xa5de, 0xa5e5, 0xa8c0, 0xa8c7, 0xa8ce, \
         0xa9f4, 0xa9fb, 0xaa02, 0xab0f, 0xab16, 0xab1d, 0xab24, 0xab2b, 0xab32, 0xae1d, 0xae26, \
         0xae2f, 0xae38, 0xaf59, 0xaf62, 0xaf6b, 0xa51c, 0xa50a, \
         0x165BB, 0x168B6, 0x17710, 0x16492, 0x16322]
chest_item_values = [30000, 10000, 200000, 10000, 80, 800, 3800, 4000, 6000, 200, 15000, 10000, 32000, \
               8000, 50000, 50000, 10000, 10000, 50, 50, 300, 40, 1000, 2500, 800, 200, 10000, \
               15000, 5000, 5000, 10480, 5000, 200, 23200, 15000, 100000, 200, 10000, 8000, 5000, \
               200, 100000, 20000, 100000, 2000]
               
weapon_types = [0x06, 0x08, 0x07, 0x0B, 0x0C, 18, 17, 19, 20, 26, 34, 5, 9, 13, 14, 15, 16, 21, 22, 23, 3, 4, 27, 28, 29]

armor_flags = [0x04, 0x08, 0x10, 0x20]

story_items = [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x1f, 0x7e, 0x7f]

def RandomizeFFLRomBytes(filebytes, monstercsvpath, ffl2bytes, seed, options, options_numbers):

    encounter_meat_levels = ReadAllEncounterCharacterMeatLevels(filebytes)
    character_abils = ReadAllCharacterAbilities(filebytes)
    original_item_details = [ReadItemToDict(filebytes, idx) for idx in range(0x00, 0xff)]

    if options[MUTANT_ABILITIES]:
        RandomizeMutantAbilityLearnList(filebytes)

    if options[ARMOR]:
        RandomizeArmor(filebytes)
        
    if options[COMBAT_ITEMS]:
        RandomizeCombatItems(filebytes)
    
    if options[CHARACTER_ITEMS]:
        RewriteHumanAndMutantItems(filebytes, character_abils)
        
    if options[ENEMY_ITEMS]:
        RewriteNonMonsterEnemyItems(filebytes, character_abils, original_item_details)

    if options[SHOPS] or options[CHESTS]:
        # Try to get the lowest possible number of unused equipment items,
        # i.e. those that doesn't appear in any shop or chest
        best_filebytes = list(filebytes)
        best_score = 99999
        attempts = 0
        max_attempts = 500
        while attempts < max_attempts:
            attempts += 1
            if options[SHOPS]:
                RandomizeEquipmentShops(filebytes)
            if options[CHESTS]:
                RandomizeChests(filebytes)
            num_unused = len(GetUnusedEquipment(filebytes))
            # print("attempt", attempts, "score", num_unused)
            if num_unused < best_score:
                best_score = num_unused
                best_filebytes = list(filebytes)
                # print("new best!")
            if num_unused <= 6: # 6 seems to be the best we're currently likely to get within a reasonable time
                break
        for i in range(0, len(filebytes)):
            filebytes[i] = best_filebytes[i]

    if options[MONSTERS]:
        RandomizeMonsters(filebytes, character_abils, monstercsvpath)
    
    WriteAllCharacterAbilities(filebytes, character_abils)

    if options[ENCOUNTERS]:
        for encounter_id in range(0, 0x80):
            RandomizeEncounterMonstersByMeatLevel(filebytes, encounter_id, encounter_meat_levels[encounter_id], options_numbers[ENCOUNTER_LEVEL_ADJUST])

    if options[GUILD_MONSTERS]:
        RandomizeGuildMonsters(filebytes)
        
    if options[HP_TABLE]:
        RandomizeHPTable(filebytes)
        
    if options[MUTANT_RACE]:
        ReplaceMutantRace(filebytes)
        
    if options[MEAT]:
        RandomizeMeatTransformationTable(filebytes)
        RandomizeMeatResultLists(filebytes, options_numbers[TRANSFORMATION_LEVEL_ADJUST])

    if options[TOWER]:
        RandomizeFirstTowerSection(filebytes)
        RandomizeSecondTowerSection(filebytes)
        RandomizeThirdTowerSection(filebytes)
        RandomizeFourthTowerSection(filebytes)
        
    if options[DUNGEONS]:
        RandomizeBanditCaveRooms(filebytes)
        RandomizeOceanCaves(filebytes)
        RandomizeDragonPalaceRooms(filebytes)
        RandomizeUnderseaCave(filebytes)
        
    if options[SKYSCRAPER]:
        RandomizeRuinsSkyscraper(filebytes)
        
    if options_numbers[MONSTER_GOLD_OFFSET_ADJUST] > 0:
        AdjustMonsterGoldOffset(filebytes, options_numbers[MONSTER_GOLD_OFFSET_ADJUST])
    
    if(abs(options_numbers[GOLD_TABLE_AMOUNT_MULTIPLIER] - 1.0) > 0.001):
        AdjustGoldTableValues(filebytes, options_numbers[GOLD_TABLE_AMOUNT_MULTIPLIER])
        
    if options[SMALL_PICS]:
        RandomizeSmallPics(filebytes, ffl2bytes)
        
    if options[WORLD_MAPS]:
        RandomlyGenerateContinentMap(filebytes)
        RandomlyGenerateOceanMap(filebytes)
        RandomlyGenerateUnderseaMap(filebytes)
        
    if options[DUNGEON_MAPS]:
        RandomlyGenerateBanditCaveMap(filebytes)
        RandomlyGenerateCastleSwordMap(filebytes)
        RandomlyGenerateOceanCaves1Map(filebytes)
        RandomlyGenerateOceanCaves2Map(filebytes)
        RandomlyGenerateUnderseaCavesMap(filebytes)
        RandomlyGenerateDragonPalaceMap(filebytes)

    if options[TOWER_MAPS]:
        RandomlyGenerateFirstTowerSection(filebytes)
        RandomlyGenerateSecondTowerSection(filebytes)
        RandomlyGenerateThirdTowerSection(filebytes)
        RandomlyGenerateFourthTowerSection(filebytes)
        
    WriteSeedTextToTitleScreen(filebytes, seed)

    return

def RandomizeMutantAbilityLearnList(filebytes):

    remaining_ability_ids = list(range(0x80, 0xfc))
    ability_ids = []
    while len(ability_ids) < 31:
        abil_pick = random.choice(remaining_ability_ids)
        abil_type = ReadItemType(filebytes, abil_pick)
        # Don't pick abilities of type Strike S (0x06) or Strike A (0x0b) or Steal (0x24)
        if not (abil_type in [0x06, 0x0b, 0x24]):
            ability_ids.append(abil_pick)
            remaining_ability_ids.remove(abil_pick)

    # construct a frequency table of abilities by counting how many times they're used in character definitions
    abil_frequencies = [0 for i in range(0, 256)]
    for idx in range(0x0001b321, 0x0001b321 + 961):
        abil = filebytes[idx]
        abil_frequencies[abil] += 1

    # sort ability_ids by frequency (most frequent first)
    ability_ids = sorted(ability_ids, key = lambda x: -1*abil_frequencies[x])

    for i in range(0, len(ability_ids)):
        # look up number of uses of the ability
        abil_id = ability_ids[i]
        uses_idx = 0x00014647 + (abil_id * 8)
        num_uses = filebytes[uses_idx]

        # write to the mutation ability table
        filebytes[0x0001bf0f + (2*i)] = abil_id
        filebytes[0x0001bf0f + (2*i) + 1] = num_uses

    return

def RandomizeHPTable(filebytes):

    # Randomize the first value to between 100% and 150% of its original value

    RandomizeByteWithinMultipliers(filebytes, 0x0001b254, 1.0, 1.5)

    for i in range(1, 32):
        # Read current value (2 bytes)
        val = ReadHPTableValue(filebytes, i)

        # Randomize to between 75% and 125% of original value
        new_val = random.uniform(0.75 * val, 1.25 * val)
        new_val = int(new_val)
        new_val = max(new_val, 0)
        new_val = min(new_val, 0xffff)

        # Write value (2 bytes)
        WriteHPTableValue(filebytes, i, new_val)

    return

def ReadHPTableValue(filebytes, i):
    idx = 0x0001b254 + (2 * i)
    val = filebytes[idx]
    val += (filebytes[idx + 1] * 0x100)

    return val

def WriteHPTableValue(filebytes, i, new_val):
    idx = 0x0001b254 + (2 * i)
    filebytes[idx] = (new_val & 0xff)
    filebytes[idx + 1] = ((new_val & 0xff00) >> 8)

    return
        

def RandomizeByteWithinMultipliers(filebytes, idx, min_mult, max_mult):
    val = filebytes[idx]
    new_val = random.uniform(min_mult * val, max_mult * val)
    new_val_int = int(new_val)
    new_val_int = min(new_val_int, 0xff)
    new_val_int = max(new_val_int, 0x00)
    filebytes[idx] = new_val_int

    return

def RandomizeEquipmentShops(filebytes):

    for i in range(0, len(shop_min_costs)):

        min_cost = shop_min_costs[i]
        max_cost = shop_max_costs[i] * 1.2

        shop_start_idx = equipment_shop_addrs[i]

        # Need to be able to buy battle sword to advance the story.
        # For now, keep battle sword in any shops that contain it
        contains_battle_sword = shop_contains_battle_sword[i]

        new_shop_items = []

        if shop_equipment_start_idx[i] == 0:
            if contains_battle_sword:
                new_shop_items.append(0x23)
            
        while len(new_shop_items) < (10 - shop_equipment_start_idx[i]):
            # eligible items for shops are 0x0b, 0x02, 0x1b, and 0x20-0x79 inclusive
            # 0x0b is DOOR - I'm including it because it might not appear in a chest
            pick = random.randrange(0x20, 0x7d)
            if pick == 0x7a:
                pick = 0x02
            if pick == 0x7b:
                pick = 0x1b
            if pick == 0x7c:
                pick = 0x0b

            if pick in new_shop_items:
                continue

            item_cost = ReadGPCost(filebytes, 0x00017e10 + (3 * pick))

            if (item_cost > 0) and (item_cost <= max_cost) and (item_cost >= min_cost):
                new_shop_items.append(pick)

        # sort new shop items by GP cost
        new_shop_items.sort(key = lambda x: ReadItemCost(filebytes, x))

        for j in range(0, len(new_shop_items)):
            filebytes[shop_start_idx + shop_equipment_start_idx[i] + j] = new_shop_items[j]

    return

def RandomizeMonsters(filebytes, abils, monstercsvpath):
    meatLevels = [\
        [0, 2, 4, 5, 12, 14], \
        [1, 2, 5, 8, 12, 14], \
        [3, 4, 6, 8, 12, 14], \
        [0, 6, 7, 8, 12, 14], \
        [3, 4, 7, 8, 12, 14], \
        [1, 3, 6, 9, 12, 14], \
        [0, 3, 7, 9, 12, 14], \
        [2, 4, 6, 9, 12, 14], \
        [1, 4, 6, 9, 12, 14], \
        [3, 5, 7, 9, 12, 14], \
        [1, 6, 7, 9, 12, 14], \
        [0, 1, 2, 10, 12, 14], \
        [0, 3, 5, 10, 12, 14], \
        [0, 1, 7, 10, 13, 14], \
        [3, 5, 8, 10, 13, 14], \
        [3, 6, 8, 11, 13, 14], \
        [0, 3, 9, 11, 13, 14], \
        [1, 7, 9, 11, 13, 14], \
        [2, 6, 10, 11, 13, 14], \
        [4, 5, 10, 11, 13, 14], \
        [0, 2, 8, 11, 13, 14], \
        [1, 2, 8, 11, 13, 14], \
        [4, 7, 8, 11, 13, 14], \
        [0, 5, 9, 11, 13, 14], \
        [6, 7, 9, 11, 13, 14]\
        ]

    lpics = [0, 1, 2, 3, 4, 5, 6, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 32, 33, 34, 35, 36, 37, 38]

    # sanity check
    if not (len(meatLevels) == len(lpics)):
        raise Exception("Error: length mismatch! " + str(len(meatLevels)) + " meatLevels ", + str(len(lpics)) + " lpics")

    csv_monsters = []
    with open(monstercsvpath, mode='r') as f:
        csvFile = csv.DictReader(f)
        for line in csvFile:
            csv_monsters.append(line)

    success = False
    while not success:
        random.shuffle(meatLevels)

        game_monsters = []
        for i in range(0, len(lpics)):
            lpic = lpics[i]
            lpic_str = str(lpic)
            for j in range(0, 6):
                meatLevel = meatLevels[i][j]
                meatLevel_str = str(meatLevel)
                matching_monsters = [m for m in csv_monsters if ((m['MeatLevel'] == meatLevel_str) and (m['LPic'] == lpic_str))]
                if len(matching_monsters) < 1:
                    raise Exception("Error: failed to find monster in CSV file with MeatLevel " + meatLevel_str + " and LPic " + lpic_str)
                game_monsters.append(random.choice(matching_monsters))

        success = WriteMonstersToGame(filebytes, abils, game_monsters)

    return

def WriteMonstersToGame(filebytes, abils, game_monsters):

    success = True

    # Check the total number of abilities is <= 991 (the maximum)
    ParseMonsterAbilitiesIntoCharacterAbilities(abils, game_monsters)
    total_num_abils = sum([len(i) for i in abils])
    if total_num_abils > 991:
        success = False

    if success:
        # Write the race / meat drop / num abilities bytes.
        # All monsters are "Monster" race, meat drop 3.
        # If we start to randomize race and meat drop, this will need to change
        # (we'll have to figure out how those values are packed into the byte)
        for monsteridx in range(0, len(game_monsters)):
            filebytes[0x0001aae8 + (9 * monsteridx)] = 0x7b + (len(abils[monsteridx]) * 8)

        # Init Type bytes. Each byte represents the Type for two monsters
        for addr in range(0x0001b1f0, 0x0001b1f0 + 0x64): # 0x64 == 0xc8 / 2
            filebytes[addr] = 0

        for monsteridx in range(0, len(game_monsters)):
            WriteMonsterData(filebytes, monsteridx, game_monsters[monsteridx])

    return success

def WriteMonsterData(filebytes, monsteridx, monsterdata):
    WriteCharacterName(filebytes, monsteridx, monsterdata['Name'])

    # Init SPic/MeatLevel byte to 0
    filebytes[0x0000b438 + monsteridx] = 0
    # Init gold table index byte to 0
    filebytes[0x0001aaee + (monsteridx * 9)] = 0
    
    WriteCharacterHPTableIndex(filebytes, monsteridx, int(monsterdata['HPOffset']))
    WriteCharacterStrength(filebytes, monsteridx, int(monsterdata['Strength']))
    WriteCharacterDefense(filebytes, monsteridx, int(monsterdata['Defense']))
    WriteCharacterAgility(filebytes, monsteridx, int(monsterdata['Agility']))
    WriteCharacterMana(filebytes, monsteridx, int(monsterdata['Mana']))
    WriteCharacterGoldTableIndex(filebytes, monsteridx, int(monsterdata['GOffset']))
    WriteCharacterSPic(filebytes, monsteridx, int(monsterdata['SPic']))
    WriteCharacterLPic(filebytes, monsteridx, int(monsterdata['LPic']))
    WriteCharacterType(filebytes, monsteridx, int(monsterdata['Type']))
    WriteMeatLevel(filebytes, monsteridx, int(monsterdata['MeatLevel']))
    return

def RandomizeGuildMonsters(filebytes):
    guild_meat_levels = [0, 0, 1, 7, 8, 11]
    for gidx in range(0, 6):
        new_monsters = []
        # count number of monsters in guild
        monster_idxs = []
        for cidx in range(0, 8):
            if ReadGuildCharacter(filebytes, gidx, cidx) < 0x96:
                monster_idxs.append(cidx)
        while len(new_monsters) < len(monster_idxs):
            idx_pick = random.choice(range(0, 0x96))
            if ReadMeatLevel(filebytes, idx_pick) == guild_meat_levels[gidx]:
                if not idx_pick in new_monsters:
                    new_monsters.append(idx_pick)
        for idx in range(0, len(monster_idxs)):
            WriteGuildCharacter(filebytes, gidx, monster_idxs[idx], new_monsters[idx])

def WriteCharacterName(filebytes, idx, name):
    namelen = min(len(name), 8)
    for i in range(0, namelen):
        filebytes[0x00014000 + (idx * 8) + i] = ASCIIValueToFFLNameText(ord(name[i]))
    for i in range(namelen, 8):
        filebytes[0x00014000 + (idx * 8) + i] = ASCIIValueToFFLNameText(ord(' '))
    return

def WriteCharacterHPTableIndex(filebytes, idx, hp_offset):
    filebytes[0x0001aae9 + (idx * 9)] = hp_offset
    return

def ReadAllCharacterAbilities(filebytes):

    character_abilities = []
    for i in range(0, 0xc8):
        character_abilities.append(ReadCharacterAbilList(filebytes, i))

    return character_abilities

def ParseMonsterAbilitiesIntoCharacterAbilities(abils, game_monsters):
    for monster_idx in range(0, len(game_monsters)):
        monster = game_monsters[monster_idx]
        abils[monster_idx] = []
        for abil_idx in range(0, 8):
            abil_str = "Slot" + str(abil_idx)
            if not (monster[abil_str] == "255"):
                abils[monster_idx].append(int(monster[abil_str]))
    return

def WriteAllCharacterAbilities(filebytes, character_abilities):
    if len(character_abilities) != 0xc8:
        raise Exception("Error: wrong number of characters in WriteAllCharacterAbilities: " + str(len(character_abilities)))
    abil_idx_offset = 0x7321
    for i in range(0, 0xc8):
        char_abils = character_abilities[i]
        WriteCharacterAbilOffset(filebytes, i, abil_idx_offset)
        for abil_idx in range(0, len(char_abils)):
            filebytes[0x00014000 + abil_idx_offset] = char_abils[abil_idx]
            abil_idx_offset += 1
    # write final abil offset
    WriteCharacterAbilOffset(filebytes, 0xc8, abil_idx_offset)
    return

def ReadGPCost(filebytes, startidx):

    # GP amounts are encoded in a strange way:
    # for example, 6789GP is encoded as 0x00 0x67 0x89
    # for example, 10480GP is encoded as 0x01 0x04 0x80
    
    cost = 0

    dig = ((filebytes[startidx] & 0xf0) / 0x10)
    cost += (dig * 100000)
    dig = (filebytes[startidx] & 0x0f)
    cost += (dig * 10000)

    dig = ((filebytes[startidx + 1] & 0xf0) / 0x10)
    cost += (dig * 1000)
    dig = (filebytes[startidx + 1] & 0x0f)
    cost += (dig * 100)

    dig = ((filebytes[startidx + 2] & 0xf0) / 0x10)
    cost += (dig * 10)
    dig = (filebytes[startidx + 2] & 0x0f)
    cost += (dig * 1)

    return int(cost)

def WriteGPCost(filebytes, startidx, cost):

    # GP amounts are encoded in a strange way:
    # for example, 6789GP is encoded as 0x00 0x67 0x89
    # for example, 10480GP is encoded as 0x01 0x04 0x80
    
    remainder = cost

    digit = (remainder % 10)
    byte = digit
    remainder -= digit
    digit = int((remainder % 100) / 10)
    byte += (0x10 * digit)
    remainder -= (digit * 10)
    filebytes[startidx + 2] = byte

    digit = int((remainder % 1000) / 100)
    byte = digit
    remainder -= (digit * 100)
    digit = int((remainder % 10000) / 1000)
    byte += (0x10 * digit)
    remainder -= (digit * 1000)
    filebytes[startidx + 1] = byte

    digit = int((remainder % 100000) / 10000)
    byte = digit
    remainder -= (digit * 10000)
    digit = int((remainder % 1000000) / 100000)
    byte += (0x10 * digit)
    filebytes[startidx] = byte

    return int(cost)

def ReadItemCost(filebytes, item_id):
    return ReadGPCost(filebytes, 0x00017e10 + (3 * item_id))

def WriteItemCost(filebytes, item_id, cost):
    WriteGPCost(filebytes, 0x00017e10 + (3 * item_id), cost)
    return

def ReadItemType(filebytes, item_id):
    return filebytes[0x0001b702 + (item_id * 8)]

def WriteItemType(filebytes, item_id, val):
    filebytes[0x0001b702 + (item_id * 8)] = val
    return

def ReadItemUses(filebytes, item_id):
    return filebytes[0x00014647 + (item_id * 8)]

def WriteItemUses(filebytes, item_id, val):
    filebytes[0x00014647 + (item_id * 8)] = val
    return

def ReadItemFlagsA(filebytes, item_id):
    return filebytes[0x0001b700 + (item_id * 8)]

def WriteItemFlagsA(filebytes, item_id, val):
    filebytes[0x0001b700 + (item_id * 8)] = val
    return

def ReadItemFlagsB(filebytes, item_id):
    return filebytes[0x0001b701 + (item_id * 8)]

def WriteItemFlagsB(filebytes, item_id, val):
    filebytes[0x0001b701 + (item_id * 8)] = val
    return

def ReadItemAltUses(filebytes, item_id):
    return filebytes[0x0001b703 + (item_id * 8)]

def WriteItemAltUses(filebytes, item_id, val):
    filebytes[0x0001b703 + (item_id * 8)] = val
    return

def ReadItemX(filebytes, item_id):
    return filebytes[0x0001b704 + (item_id * 8)]

def WriteItemX(filebytes, item_id, val):
    filebytes[0x0001b704 + (item_id * 8)] = val
    return

def ReadItemY(filebytes, item_id):
    return filebytes[0x0001b705 + (item_id * 8)]

def WriteItemY(filebytes, item_id, val):
    filebytes[0x0001b705 + (item_id * 8)] = val
    return

def ReadItemGFX(filebytes, item_id):
    return filebytes[0x0001b706 + (item_id * 8)]

def WriteItemGFX(filebytes, item_id, val):
    filebytes[0x0001b706 + (item_id * 8)] = val
    return

def ReadItemGroupFlag(filebytes, item_id):
    return (filebytes[0x0001b707 + (item_id * 8)] & 0x80)

def WriteItemGroupFlag(filebytes, item_id, val):
    filebytes[0x0001b707 + (item_id * 8)] |= (val & 0x80)
    return

def ReadItemSFX(filebytes, item_id):
    return (filebytes[0x0001b707 + (item_id * 8)] & 0x7f)

def WriteItemSFX(filebytes, item_id, val):
    filebytes[0x0001b707 + (item_id * 8)] |= (val & 0x7f)
    return

def ReadMeatLevel(filebytes, character_id):
    return (filebytes[0x0000b438 + character_id] & 0x0f)

def WriteMeatLevel(filebytes, character_id, val):
    filebytes[0x0000b438 + character_id] |= val
    return

def ReadEncounterCharacter(filebytes, encounter_idx, character_pos):
    return filebytes[0x0001a868 + (encounter_idx * 5) + character_pos]

def WriteEncounterCharacter(filebytes, encounter_idx, character_pos, character_id):
    filebytes[0x0001a868 + (encounter_idx * 5) + character_pos] = character_id

# Returns a list which contains one list per encounter, each of which contain the meat levels for the three characters in the encounter
def ReadAllEncounterCharacterMeatLevels(filebytes):
    meat_levels = GetMeatLevelsDict(filebytes)
    # add the bosses
    for i in range(0xbd, 0xc8):
        meat_levels[i] = ReadMeatLevel(filebytes, i)
    allencountermeatlevels = []
    for encidx in range(0, 0x80):
        encountermeatlevels = []
        for charidx in range(0, 3):
            char = ReadEncounterCharacter(filebytes, encidx, charidx)
            encountermeatlevels.append(meat_levels[char])
        allencountermeatlevels.append(encountermeatlevels)
    return allencountermeatlevels

def GetMeatLevelsDict(filebytes):
    # Initialize with pseudo meat levels for non-monster enemies
    meat_levels = { 0x96:0, 0x97:2, 0x98:7, 0x99:9, 0x9a:12, 0x9b:0, 0x9c:5, 0x9d:9, 0x9e:11, 0x9f:13, \
        0xa0:1, 0xa1:3, 0xa2:4, 0xa3:8, 0xa4:11, 0xa5:13, 0xa6:0, 0xa7:3, 0xa8:7, 0xa9:9, 0xaa:11, 0xab:13, 0xac:14 }
        
    # Read the actual meat levels for monster enemies
    for i in range(0x00, 0x96):
        meat_levels[i] = ReadMeatLevel(filebytes, i)

    return meat_levels
    
# Picks random monsters for the specified encounter which match the target meat levels
# Only replaces monsters (0x00-0x95). Does not replace non-monster enemies or bosses (> 0x96)
def RandomizeEncounterMonstersByMeatLevel(filebytes, encounter_idx, target_meat_levels, encounter_level_adjust):

    meat_levels = GetMeatLevelsDict(filebytes)
        
    # List of characters that will never be replaced: which are the bosses
    non_replace_characters = [0xa0, 0xa6, 0xac, 0xbd, 0xbe, 0xbf, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7]

    new_encounter_characters = []
    for charpos in range(0, 3):
        encounter_character = ReadEncounterCharacter(filebytes, encounter_idx, charpos)
        new_encounter_characters.append(encounter_character)
        if not encounter_character in non_replace_characters:
            target_meat_level = target_meat_levels[charpos]
            target_meat_level += encounter_level_adjust
            target_meat_level = max(0, target_meat_level)
            target_meat_level = min(target_meat_level, 0xf)
            success = False
            while((not success) and (target_meat_level >= 0)):
                success = True
                # Starting from a random offset and wrapping around, take the first monster with a matching meat level
                # which doesn't already appear in the encounter
                random_offset = random.randrange(0, 0xac)
                for i in range(0, 0xad):
                    idx = (i + random_offset) % 0xad
                    if (not idx in new_encounter_characters) and (not idx in non_replace_characters):
                        if(meat_levels[idx] == target_meat_level):
                            new_encounter_characters[charpos] = idx
                            success = True
                            break
                if not success:
                    # Reduce the target meat level and try again
                    target_meat_level -= 1
    
    for charpos in range(0, 3):
        WriteEncounterCharacter(filebytes, encounter_idx, charpos, new_encounter_characters[charpos])

# Converts FFL name text byte value to ASCII byte value.
# Only converts 0-9, a-z, A-Z and selected symbols - does not convert the multi-character bytes used in dialog text
def FFLNameTextToASCII(byte):
    if((byte >= 0x80) and (byte <= 0x89)):
        # FFL 0x80-0x89 map to ASCII 0x30-0x39: numbers
        return byte - 0x50
    if((byte >= 0x8A) and (byte <= 0xA3)):
        # FFL 0x8A-0xA3 map to ASCII 0x41-0x5A: A-Z
        return byte - 0x49
    if((byte >= 0xA4) and (byte <= 0xBD)):
        # FFL 0xA4-0xBD map to ASCII 0x61-0x7A: a-z
        return byte - 0x43
    if(byte == 0xe8): # armor symbol
        return ord('&')
    if(byte == 0xe9): # shield symbol
        return ord('£')
    if(byte == 0xea): # gauntlet symbol
        return ord('*')
    if(byte == 0xeb): # shoe symbol
        return ord('~')
    if(byte == 0xec): # sword symbol
        return ord('$')
    if(byte == 0xed): # helm symbol
        return ord('@')
    if(byte == 0xee): # gun symbol
        return ord('^')
    if(byte == 0xef): # book symbol
        return ord('%')
    if(byte == 0xff):
        return ord(' ')
    if(byte == 0xf2):
        return ord('-')
    if(byte == 0x43):
        return ord('>') # resist
    if(byte == 0x44):
        return ord('<') # weakness
    if(byte == 0x45):
        return ord('/')
    if(byte == 0xf0):
        return ord('.')
    if(byte == 0x42): # heart symbol
        return ord('#')

    return ord('_')

# Converts ASCII byte value to FFL name text byte value.
# Only converts 0-9, a-z, A-Z and selected symbols - does not convert the multi-character bytes used in dialog text
def ASCIIValueToFFLNameText(val):
    if((val >= 0x30) and (val <= 0x39)):
        # Number
        return val + 0x50
    if((val >= 0x41) and (val <= 0x5A)):
        # Upper case letter
        return val + 0x49
    if((val >= 0x61) and (val <= 0x7A)):
        # Lower case letter
        return val + 0x43
    if val == ord('&'):
        return 0xe8 # armor symbol
    if val == ord('£'):
        return 0xe9 # shield symbol
    if val == ord('*'):
        return 0xea # gauntlet symbol
    if val == ord('~'):
        return 0xeb # shoe symbol
    if val == ord('$'):
        return 0xec # sword symbol
    if val == ord('@'):
        return 0xed # helm symbol
    if val == ord('^'):
        return 0xee # gun symbol
    if val == ord('%'):
        return 0xef # book symbol
    if val == ord(' '):
        return 0xff
    if val == ord('-'):
        return 0xf2
    if val == ord('>'): #resist
        return 0x43
    if val == ord('<'): #weakness
        return 0x44
    if val == ord('/'):
        return 0x45
    if val == ord('.'):
        return 0xf0
    if val == ord('#'):
        return 0x42

    return 0xff

def ReadMonsterName(filebytes, idx):
    name = ""
    for i in range(0, 8):
        name += chr(FFLNameTextToASCII(filebytes[0x00014000 + (idx * 8) + i]))
    return name

def ReadCharacterStrength(filebytes, idx):
    return filebytes[0x0001aaea + (idx * 9)]

def WriteCharacterStrength(filebytes, idx, val):
    filebytes[0x0001aaea + (idx * 9)] = val
        
def ReadCharacterDefense(filebytes, idx):
    return filebytes[0x0001aaeb + (idx * 9)]

def WriteCharacterDefense(filebytes, idx, val):
    filebytes[0x0001aaeb + (idx * 9)] = val

def ReadCharacterAgility(filebytes, idx):
    return filebytes[0x0001aaec + (idx * 9)]

def WriteCharacterAgility(filebytes, idx, val):
    filebytes[0x0001aaec + (idx * 9)] = val

def ReadCharacterMana(filebytes, idx):
    return filebytes[0x0001aaed + (idx * 9)]

def WriteCharacterMana(filebytes, idx, val):
    filebytes[0x0001aaed + (idx * 9)] = val

def ReadCharacterHPTableIndex(filebytes, idx):
    return filebytes[0x0001aae9 + (idx * 9)]

def ReadCharacterGoldTableIndex(filebytes, idx):
    return filebytes[0x0001aaee + (idx * 9)] & 0x0f

def WriteCharacterGoldTableIndex(filebytes, idx, val):
    filebytes[0x0001aaee + (idx * 9)] |= val

def ReadCharacterSPic(filebytes, idx):
    return (filebytes[0x0000b438 + idx] & 0xf0) >> 4

def WriteCharacterSPic(filebytes, idx, val):
    filebytes[0x0000b438 + idx] |= (val << 4)

def ReadCharacterLPic(filebytes, idx):
    return filebytes[0x0000b900 + idx]

def WriteCharacterLPic(filebytes, idx, val):
    filebytes[0x0000b900 + idx] = val

def ReadCharacterType(filebytes, idx):
    addr = (idx >> 1) + 0x0001b1f0
    val = filebytes[addr]
    if idx % 2 == 0:
        return (val & 0xf0) >> 4
    return (val & 0x0f)

def WriteCharacterType(filebytes, idx, val):
    addr = (idx >> 1) + 0x0001b1f0
    if idx % 2 == 0:
        filebytes[addr] |= (val << 4)
    else:
        filebytes[addr] |= val

def ReadCharacterAbilOffset(filebytes, idx):
    # two bytes
    offset = filebytes[0x0001aaf0 + (idx * 9)] * 0x100
    offset += filebytes[0x0001aaef + (idx * 9)]
    return offset

def WriteCharacterAbilOffset(filebytes, idx, offset):
    # two bytes
    offset_high = (offset & 0xff00) >> 8
    offset_low = offset & 0x00ff
    filebytes[0x0001aaf0 + (idx * 9)] = offset_high
    filebytes[0x0001aaef + (idx * 9)] = offset_low
    return

def ReadCharacterAbilList(filebytes, idx):
    # Assume each character's abilities are between their abil offset
    # and the next character's abil offset.
    # TODO read the race/meat drop/num abils byte and use that instead
    abil_list = []
    offset = ReadCharacterAbilOffset(filebytes, idx)
    next_offset = ReadCharacterAbilOffset(filebytes, idx + 1)
    if idx == 0xc7: # CREATOR
        next_offset = offset + 8 # has 8 abils
    for i in range(offset, next_offset):
        abil_list.append(filebytes[0x00014000 + i])
    return abil_list

# Reads value from the G table used for fight rewards. Each value is two bytes
def ReadGoldTableValue(filebytes, i):
    startidx = 0x0001b2a4 + (i * 2)
    cost = 0

    dig = ((filebytes[startidx] & 0xf0) / 0x10)
    cost += (dig * 1000)
    dig = (filebytes[startidx] & 0x0f)
    cost += (dig * 100)

    dig = ((filebytes[startidx + 1] & 0xf0) / 0x10)
    cost += (dig * 10)
    dig = (filebytes[startidx + 1] & 0x0f)
    cost += (dig * 1)

    return int(cost)

# Writes value to the G table used for fight rewards. Each value is two bytes
def WriteGoldTableValue(filebytes, i, value):
    startidx = 0x0001b2a4 + (i * 2)
    remaining_value = value
    
    units_digit = (remaining_value % 10)
    remaining_value -= units_digit
    tens_digit = int((remaining_value % 100) / 10)
    remaining_value -= (tens_digit * 10)
    filebytes[0x0001b2a4 + (i * 2) + 1] = units_digit + (tens_digit * 0x10)
    
    hundreds_digit = int((remaining_value % 1000) / 100)
    remaining_value -= (hundreds_digit * 100)
    thousands_digit = int((remaining_value % 10000) / 1000)
    remaining_value -= (thousands_digit * 1000)
    filebytes[0x0001b2a4 + (i * 2)] = hundreds_digit + (thousands_digit * 0x10)

    return

def ReadItemName(filebytes, idx):
    name = ""
    for i in range(0, 7):
        name += chr(FFLNameTextToASCII(filebytes[0x00014640 + (idx * 8) + i]))
    return name
    
def WriteItemName(filebytes, idx, name):
    for i in range(0, min(7, len(name))):
        filebytes[0x00014640 + (idx * 8) + i] = ASCIIValueToFFLNameText(ord(name[i]))
    for i in range(len(name), 7):
        filebytes[0x00014640 + (idx * 8) + i] = ASCIIValueToFFLNameText(ord(' '))
    return

def ReadGuildCharacter(filebytes, guildidx, charidx):
    return filebytes[0x00017f90 + (guildidx * 8) + charidx]

def WriteGuildCharacter(filebytes, guildidx, charidx, char):
    filebytes[0x00017f90 + (guildidx * 8) + charidx] = char
    return

def WriteMutantLearnAbilityRate(filebytes, val):
    filebytes[0x0001bf00] = val
    return

def WriteMutantGainHRate(filebytes, val):
    filebytes[0x0001bf01] = val
    return

def WriteMutantGainMRate(filebytes, val):
    filebytes[0x0001bf02] = val
    return
    
def WriteMutantGainARate(filebytes, val):
    filebytes[0x0001bf03] = val
    return

def WriteMutantGainSRate(filebytes, val):
    filebytes[0x0001bf04] = val
    return

def WriteMutantGainDRate(filebytes, val):
    filebytes[0x0001bf05] = val
    return

def WriteMutantAlterUsesRate(filebytes, val):
    filebytes[0x0001bf06] = val
    return

def WriteMutantGainHAmount(filebytes, mingain, maxgain):
    byteval = maxgain & 0x0f
    byteval += (mingain & 0x0f) * 0x10
    filebytes[0x0001bf0a] = byteval
    return

def WriteMutantGainSAmount(filebytes, mingain, maxgain):
    byteval = maxgain & 0x0f
    byteval += (mingain & 0x0f) * 0x10
    filebytes[0x0001bf0b] = byteval
    return

def WriteMutantGainDAmount(filebytes, mingain, maxgain):
    byteval = maxgain & 0x0f
    byteval += (mingain & 0x0f) * 0x10
    filebytes[0x0001bf0c] = byteval
    return

def WriteMutantGainAAmount(filebytes, mingain, maxgain):
    byteval = maxgain & 0x0f
    byteval += (mingain & 0x0f) * 0x10
    filebytes[0x0001bf0d] = byteval
    return

def WriteMutantGainMAmount(filebytes, mingain, maxgain):
    byteval = maxgain & 0x0f
    byteval += (mingain & 0x0f) * 0x10
    filebytes[0x0001bf0e] = byteval
    return

def ReplaceMutantRace(filebytes):
    mutant_ms = [0xAF, 0xB3, 0xB7, 0xBB]
    mutant_fs = [0xB0, 0xB4, 0xB8, 0xBC]
    pick = random.choice(range(0, 4))
    if pick == 0:
        return
    if pick == 1:
        # "D-MUT"
        val = 30
        WriteMutantLearnAbilityRate(filebytes, val)
        val += 40 # gain H rate
        WriteMutantGainHRate(filebytes, val)
        val += 18 # gain M rate
        WriteMutantGainMRate(filebytes, val)
        val += 12 # gain A rate
        WriteMutantGainARate(filebytes, val)
        val += 18 # gain S rate
        WriteMutantGainSRate(filebytes, val)
        val += 20 # gain D rate
        WriteMutantGainDRate(filebytes, val)
        val += 4 # alter uses rate
        WriteMutantAlterUsesRate(filebytes, val)
        WriteMutantGainHAmount(filebytes, 10, 15)
        WriteMutantGainSAmount(filebytes, 1, 5)
        WriteMutantGainDAmount(filebytes, 1, 5)
        WriteMutantGainAAmount(filebytes, 1, 3)
        WriteMutantGainMAmount(filebytes, 1, 5)
        for char in mutant_ms:
            WriteCharacterName(filebytes, char, "D-MUT M")
        for char in mutant_fs:
            WriteCharacterName(filebytes, char, "D-MUT F")
    if pick == 2:
        # "A-MUT"
        val = 35
        WriteMutantLearnAbilityRate(filebytes, val)
        val += 30 # gain H rate
        WriteMutantGainHRate(filebytes, val)
        val += 30 # gain M rate
        WriteMutantGainMRate(filebytes, val)
        val += 34 # gain A rate
        WriteMutantGainARate(filebytes, val)
        val += 6 # gain S rate
        WriteMutantGainSRate(filebytes, val)
        val += 8 # gain D rate
        WriteMutantGainDRate(filebytes, val)
        val += 4 # alter uses rate
        WriteMutantAlterUsesRate(filebytes, val)
        WriteMutantGainHAmount(filebytes, 8, 15)
        WriteMutantGainSAmount(filebytes, 1, 3)
        WriteMutantGainDAmount(filebytes, 1, 5)
        WriteMutantGainAAmount(filebytes, 1, 5)
        WriteMutantGainMAmount(filebytes, 1, 5)
        for char in mutant_ms:
            WriteCharacterName(filebytes, char, "A-MUT M")
        for char in mutant_fs:
            WriteCharacterName(filebytes, char, "A-MUT F")
    if pick == 3:
        # "S-MUT"
        val = 35
        WriteMutantLearnAbilityRate(filebytes, val)
        val += 34 # gain H rate
        WriteMutantGainHRate(filebytes, val)
        val += 18 # gain M rate
        WriteMutantGainMRate(filebytes, val)
        val += 18 # gain A rate
        WriteMutantGainARate(filebytes, val)
        val += 30 # gain S rate
        WriteMutantGainSRate(filebytes, val)
        val += 8 # gain D rate
        WriteMutantGainDRate(filebytes, val)
        val += 4 # alter uses rate
        WriteMutantAlterUsesRate(filebytes, val)
        WriteMutantGainHAmount(filebytes, 10, 15)
        WriteMutantGainSAmount(filebytes, 1, 5)
        WriteMutantGainDAmount(filebytes, 1, 5)
        WriteMutantGainAAmount(filebytes, 1, 5)
        WriteMutantGainMAmount(filebytes, 1, 3)
        for char in mutant_ms:
            WriteCharacterName(filebytes, char, "S-MUT M")
        for char in mutant_fs:
            WriteCharacterName(filebytes, char, "S-MUT F")

    return

def RandomizeMeatTransformationTable(filebytes):
    for row in range(0, 25):
        outcomes = list(range(0, 0x19))
        outcomes = outcomes + [0xff, 0xff, 0xff, 0xff]
        random.shuffle(outcomes)
        for col in range(0, 29):
            filebytes[0x0000afd3 + (row * 29) + col] = outcomes[col]
    return
    
def RandomizeMeatResultLists(filebytes, level_adjust):
    meat_levels = GetMeatLevelsDict(filebytes)
    
    for monster_class in range(0, 25):
        for level in range(0, 16):
            target_level = level + level_adjust
            target_level = max(0, target_level)
            monster_id = -1
            
            # Check for a monster in this class with the correct meat level
            for class_member in range(0, 6):
                class_member_id = (monster_class * 6) + class_member
                if meat_levels[class_member_id] == target_level:
                    monster_id = class_member_id
                    
            if monster_id < 0:
                # Check for a monster in this class with meat level one lower
                for class_member in range(0, 6):
                    class_member_id = (monster_class * 6) + class_member
                    if meat_levels[class_member_id] == (target_level - 1):
                        monster_id = class_member_id
                        
            if monster_id < 0:
                if random.randrange(0, 2) == 0: # 50% chance
                    # Check for a monster in this class with meat level one higher
                    for class_member in range(0, 6):
                        class_member_id = (monster_class * 6) + class_member
                        if meat_levels[class_member_id] == (target_level + 1):
                            monster_id = class_member_id
                            
            if monster_id < 0:
                # Choose a random monster from any class with the correct meat level
                id_range = 0x96
                #if random.randrange(0, 4) == 0:
                #    id_range = 0xad # Possibility of transforming into non-monster enemies!
                id_offset = random.randrange(0, id_range)
                for i in range(0, id_range):
                    check_monster_id = (i + id_offset) % id_range
                    if meat_levels[check_monster_id] == target_level:
                        monster_id = check_monster_id
                        break
                        
            if monster_id < 0:
                raise Exception("RandomizeMeatResultLists algorithm error")
            
            filebytes[0x0000b2a8 + (monster_class * 16) + level] = monster_id

    return

def RandomizeChests(filebytes):
    # Pick a random item for each chest (except chests with story items)
    # which is between 75% and 125% of the value of the original item,
    # or (20% chance) between 200% and 300% of the value
    for i in range(0, len(chest_addrs)):
        pick = 0xff
        r = random.randrange(0x80)
        valid = False
        min_cost = chest_item_values[i] * 0.75
        max_cost = chest_item_values[i] * 1.25
        if random.randrange(0, 10) < 2:
            min_cost = chest_item_values[i] * 2.0
            max_cost = chest_item_values[i] * 3.0
        for item_offset in range(0, 0x80):
            pick = (r + item_offset) % 0x80
            # exclude story items
            valid = not pick in story_items
            if valid:
                pick_cost = ReadItemCost(filebytes, pick)
                valid = ((pick_cost >= min_cost) and (pick_cost <= max_cost))
            if valid:
                break
        # If no items were found in the target price range, pick a random item (except story items)
        while (not valid):
            pick = random.randrange(0, 0x80)
            valid = not pick in story_items
        addr = chest_addrs[i]
        # print("Replacing", ReadItemName(filebytes, filebytes[addr]), "with", ReadItemName(filebytes, pick))
        filebytes[addr] = pick
    return


def ExportMeatMonstersCSV(filebytes, rompath):

    p = pathlib.Path(rompath).with_name("FFLMonsters.csv")

    f = open(p, mode='w')

    f.write("Name,HPOffset,HP,Strength,Defense,Agility,Mana,GOffset,G,SPic,LPic,Type,MeatLevel,Slot0,Slot0Text,Slot1,Slot1Text,Slot2,Slot2Text,Slot3,Slot3Text,Slot4,Slot4Text,Slot5,Slot5Text,Slot6,Slot6Text,Slot7,Slot7Text,\n")

    for idx in range(0, 0x96):

        # Name
        name = ReadMonsterName(filebytes, idx)
        name = name.strip()
        f.write(name)
        f.write(',')

        # HP
        hp_offset = ReadCharacterHPTableIndex(filebytes, idx)
        f.write(str(hp_offset))
        f.write(',')
        hp = ReadHPTableValue(filebytes, hp_offset)
        f.write(str(hp))
        f.write(',')

        # SDAM
        f.write(str(ReadCharacterStrength(filebytes, idx)))
        f.write(',')
        f.write(str(ReadCharacterDefense(filebytes, idx)))
        f.write(',')
        f.write(str(ReadCharacterAgility(filebytes, idx)))
        f.write(',')
        f.write(str(ReadCharacterMana(filebytes, idx)))
        f.write(',')

        # G
        gold_offset = ReadCharacterGoldTableIndex(filebytes, idx)
        f.write(str(gold_offset))
        f.write(',')
        gold = ReadGoldTableValue(filebytes, gold_offset)
        f.write(str(gold))
        f.write(',')

        # todo: race? meat drop?

        # SPic
        spic = ReadCharacterSPic(filebytes, idx)
        f.write(str(spic))
        f.write(',')

        # LPic
        lpic = ReadCharacterLPic(filebytes, idx)
        f.write(str(lpic))
        f.write(',')

        # Type
        t = ReadCharacterType(filebytes, idx)
        f.write(str(t))
        f.write(',')

        # MeatLevel
        meatlevel = ReadMeatLevel(filebytes, idx)
        f.write(str(meatlevel))
        f.write(',')

        # Abils
        abil_list = ReadCharacterAbilList(filebytes, idx)
        for abil in abil_list:
            f.write(str(abil))
            f.write(',')
            abilname = ReadItemName(filebytes, abil)
            abilname = abilname.strip()
            f.write(abilname)
            f.write(',')
        if len(abil_list) < 8:
            for x in range(len(abil_list), 8):
                f.write('255,-,')

        f.write('\n')

    f.close()

    return

def ExportItemsCSV(filebytes, rompath):

    p = pathlib.Path(rompath).with_name("FFLItems.csv")

    f = open(p, mode='w')

    f.write("ID,Name,Uses,Cost,FlagsA,FlagsB,Type,AltUses,X,Y,GFX,Group,SFX,UsedByChrs,Weight,\n")

    for idx in range(0, 0x80):

        # ID
        f.write(str(idx))
        f.write(',')

        # Name
        name = ReadItemName(filebytes, idx)
        name = name.strip()
        f.write(name)
        f.write(',')

        # Uses
        uses = ReadItemUses(filebytes, idx)
        f.write(str(uses))
        f.write(',')

        # Cost
        cost = ReadItemCost(filebytes, idx)
        f.write(str(cost))
        f.write(',')

        # Flags A
        flagsa = ReadItemFlagsA(filebytes, idx)
        f.write(str(flagsa))
        f.write(',')

        # Flags B
        flagsb = ReadItemFlagsB(filebytes, idx)
        f.write(str(flagsb))
        f.write(',')

        # Type
        t = ReadItemType(filebytes, idx)
        f.write(str(t))
        f.write(',')

        # Alt uses
        u = ReadItemAltUses(filebytes, idx)
        f.write(str(u))
        f.write(',')

        # X
        x = ReadItemX(filebytes, idx)
        f.write(str(x))
        f.write(',')

        # Y
        y = ReadItemY(filebytes, idx)
        f.write(str(y))
        f.write(',')

        # GFX
        gfx = ReadItemGFX(filebytes, idx)
        f.write(str(gfx))
        f.write(',')

        # Group
        gr = ReadItemGroupFlag(filebytes, idx)
        f.write(str(gr))
        f.write(',')

        # SFX
        sfx = ReadItemSFX(filebytes, idx)
        f.write(str(sfx))
        f.write(',')

        # UsedByChrs. Flag is true if the item is used by enemies. Also true for battle sword and king items.
        used_by_chrs = IsAbilUsedByEnemies(filebytes, idx) or (idx in [0x23, 0x11, 0x12, 0x13])
        f.write(str(used_by_chrs))
        f.write(',')
        
        # Weight
        f.write("1")
        f.write(",")

        f.write('\n')
        
def IsAbilUsedByEnemies(filebytes, idx):
    for chridx in range(0, 0xc8):
        if (chridx >= 0xad) and (chridx < 0xbd): # exclude guild HUMANs and MUTANTs
            continue
        if (chridx >= 0x96) and (chridx < 0xac): # exclude non-monster enemies (but not MACHINE)
            continue
        abils = ReadCharacterAbilList(filebytes, chridx)
        if idx in abils:
            return True
    return False
        
def WriteSeedTextToTitleScreen(filebytes, seed):
    seedstr = str(seed)
    while len(seedstr) < 20:
        seedstr += " "
    for i in range(0, 20):
        filebytes[0x0000ecee + i] = ASCIIValueToFFLNameText(ord(seedstr[i]))
        
    return
    
def GetCSVItemAllowedByArmorSimilarityCriterion(csv_item, helm_x_values, armor_x_values, glove_x_values, shoe_x_values, min_value_difference):
    csv_type = int(csv_item['Type'])
    csv_FlagsA = int(csv_item['FlagsA'])
    csv_x = int(csv_item['X'])
    is_helm = (csv_type == 0) and ((csv_FlagsA & 0x04) == 0x04)
    is_armor = (csv_type == 0) and ((csv_FlagsA & 0x08) == 0x08)
    is_glove = (csv_type == 0) and ((csv_FlagsA & 0x10) == 0x10)
    is_shoe = (csv_type == 0) and ((csv_FlagsA & 0x20) == 0x20)
    if is_helm:
        if GetValueTooSimilar(helm_x_values, csv_x, min_value_difference):
            # print("helm too similar", csv_item['Name'], csv_x, helm_x_values)
            return False
    if is_armor:
        if GetValueTooSimilar(armor_x_values, csv_x, min_value_difference):
            # print("armor too similar", csv_item['Name'], csv_x, armor_x_values)
            return False
    if is_glove:
        if GetValueTooSimilar(glove_x_values, csv_x, min_value_difference):
            # print("glove too similar", csv_item['Name'], csv_x, glove_x_values)
            return False
    if is_shoe:
        if GetValueTooSimilar(shoe_x_values, csv_x, min_value_difference):
            # print("shoe too similar", csv_item['Name'], csv_x, shoe_x_values)
            return False
    return True
    
def GetCSVItemAllowedByTypeSimilarityCriterion(csv_item, type_group_map, group_values, group_value_differences):
    csv_type = int(csv_item['Type'])
    csv_x = int(csv_item['X'])
    type_group = type_group_map[csv_type]
    vals = group_values[type_group]
    if csv_x < 3:
        return not csv_x in vals
    min_value_difference = group_value_differences[type_group]
    return not GetValueTooSimilar(vals, csv_x, min_value_difference)
    
def AddCSVItemXValueToExisting(chosen_item, type_group_map, group_values):
    tp = int(chosen_item['Type'])
    x = int(chosen_item['X'])
    type_group = type_group_map[tp]
    vals = group_values[type_group]
    vals.append(x)
    return

def AddArmorCSVItemXValueToExisting(csv_item, helm_x_values, armor_x_values, glove_x_values, shoe_x_values):
    csv_type = int(csv_item['Type'])
    csv_FlagsA = int(csv_item['FlagsA'])
    csv_x = int(csv_item['X'])
    is_helm = (csv_type == 0) and ((csv_FlagsA & 0x04) == 0x04)
    is_armor = (csv_type == 0) and ((csv_FlagsA & 0x08) == 0x08)
    is_glove = (csv_type == 0) and ((csv_FlagsA & 0x10) == 0x10)
    is_shoe = (csv_type == 0) and ((csv_FlagsA & 0x20) == 0x20)
    if is_helm:
        # print("adding helm value", csv_x, "to", helm_x_values)
        helm_x_values.append(csv_x)
    if is_armor:
        # print("adding armor value", csv_x, "to", armor_x_values)
        armor_x_values.append(csv_x)
    if is_glove:
        # print("adding glove value", csv_x, "to", glove_x_values)
        glove_x_values.append(csv_x)
    if is_shoe:
        # print("adding shoe value", csv_x, "to", shoe_x_values)
        shoe_x_values.append(csv_x)

    return
    
def GetValueTooSimilar(existing_values, new_value, min_difference):
    for v in existing_values:
        if abs(v - new_value) < min_difference:
            return True
    return False
    
def GetAnyFlagSet(val, acceptable_values):
    for flag in acceptable_values:
        if (val & flag) == flag:
            return True
    return False
    
def WriteCSVItemToSlot(filebytes, idx, chosen_item):
    # print("Replacing", ReadItemName(filebytes, idx), "with", chosen_item['Name'])
    # print(chosen_item)

    # Write its properties to the item slot
    WriteItemName(filebytes, idx, chosen_item['Name'])
    WriteItemUses(filebytes, idx, int(chosen_item['Uses']))
    WriteItemCost(filebytes, idx, int(chosen_item['Cost']))
    WriteItemFlagsA(filebytes, idx, int(chosen_item['FlagsA']))
    WriteItemFlagsB(filebytes, idx, int(chosen_item['FlagsB']))
    WriteItemType(filebytes, idx, int(chosen_item['Type']))
    WriteItemAltUses(filebytes, idx, int(chosen_item['AltUses']))
    WriteItemX(filebytes, idx, int(chosen_item['X']))
    WriteItemY(filebytes, idx, int(chosen_item['Y']))
    WriteItemGFX(filebytes, idx, int(chosen_item['GFX']))
    # Initialize the group flag/SFX byte
    filebytes[0x0001b707 + (idx * 8)] = 0
    WriteItemGroupFlag(filebytes, idx, int(chosen_item['Group']))
    WriteItemSFX(filebytes, idx, int(chosen_item['SFX']))
    
    return
    
def RewriteHumanAndMutantItems(filebytes, abils):
    costs = [50, 150, 1000, 15000]
    s_weapons = []
    a_weapons = []
    for cost_idx in range(0, 4):
        max_cost = costs[cost_idx]
        min_cost = 0
        if cost_idx > 0:
            min_cost = costs[cost_idx - 1]
        wpn = TryFindItemWithTypeInCostRange(filebytes, 6, min_cost, max_cost) # Strike (S)
        if wpn < 0:
            wpn = TryFindItemWithTypeInCostRange(filebytes, 17, min_cost, max_cost) # Projectile (S)
        if wpn < 0:
            wpn = TryFindItemWithTypeInCostRange(filebytes, 20, min_cost, max_cost) # Ordnance
        s_weapons.append(wpn)
        
        wpn = TryFindItemWithTypeInCostRange(filebytes, 11, min_cost, max_cost) # Strike (A)
        if wpn < 0:
            wpn = TryFindItemWithTypeInCostRange(filebytes, 18, min_cost, max_cost) # Projectile (A)
        if wpn < 0:
            wpn = TryFindItemWithTypeInCostRange(filebytes, 19, min_cost, max_cost) # Whip
        if wpn < 0:
            wpn = TryFindItemWithTypeInCostRange(filebytes, 20, min_cost, max_cost) # Ordnance
        a_weapons.append(wpn)

    for wpns in [s_weapons, a_weapons]:
        for wpn_idx in range(0, len(wpns)):
            if wpns[wpn_idx] < 0:
                if (wpn_idx > 0) and (wpns[wpn_idx - 1] >= 0):
                    wpns[wpn_idx] = wpns[wpn_idx - 1]
                else:
                    if (wpn_idx < (len(wpns) - 1)) and (wpns[wpn_idx + 1] >= 0):
                        wpns[wpn_idx] = wpns[wpn_idx + 1]
        for wpn_idx in range(0, len(wpns)):
            if wpns[wpn_idx] < 0:
                wpns[wpn_idx] = 0x00
                    

    abils[0xad][0] = s_weapons[0] # HUMAN M
    abils[0xae][0] = a_weapons[0] # HUMAN F
    abils[0xaf][4] = s_weapons[0] # MUTANT M
    abils[0xb0][4] = a_weapons[0] # MUTANT M
    abils[0xb1][0] = s_weapons[1] # HUMAN M
    abils[0xb1][1] = 0x00 # HUMAN M
    abils[0xb2][0] = a_weapons[1] # HUMAN F
    abils[0xb2][1] = 0x00 # HUMAN F
    abils[0xb3][4] = s_weapons[1] # MUTANT M
    abils[0xb4][4] = a_weapons[1] # MUTANT M
    abils[0xb5][0] = s_weapons[2] # HUMAN M
    abils[0xb6][0] = a_weapons[2] # HUMAN F
    # 0xb7 - MUTANT M with only powers
    # 0xb8 - MUTANT F with only powers
    abils[0xb9][0] = s_weapons[3] # HUMAN M
    abils[0xba][0] = a_weapons[3] # HUMAN F
    # 0xbb - MUTANT M with only powers
    # 0xbc - MUTANT F with only powers

    return
    
def TryFindItemWithTypeInCostRange(filebytes, abiltype, mincost, maxcost):
    for idx in range(0x00, 0x80):
        item_cost = ReadItemCost(filebytes, idx)
        if (item_cost >= mincost) and (item_cost <= maxcost):
            if (ReadItemType(filebytes, idx) == abiltype):
                return idx
    return -1
    
def RandomizeArmor(filebytes):
    new_items = []
    GenerateHelms(new_items)
    GenerateArmors(new_items)
    GenerateGloves(new_items)
    GenerateShoes(new_items)
    old_items = []
    for idx in range(0x00, 0x80):
        if idx in [0x11, 0x12, 0x13]: # KING items
            continue
        if not GetItemIsArmor(filebytes, idx):
            continue
        if IsAbilUsedByEnemies(filebytes, idx):
            continue
        old_items.append(ReadItemToDict(filebytes, idx))
        
    cost_ranges = [[0, 50], [51, 100], [101, 200], [201, 350], [351, 500], [501, 1000], [1001, 5000], [5001, 10000], [10001, 20000], [20001, 9999999]]
    AdjustWeightsByCostRange(cost_ranges, old_items, new_items)
    
    helm_x_values = []
    armor_x_values = []
    glove_x_values = []
    shoe_x_values = []

    rom_eligible_items = [d['ID'] for d in old_items]
    random.shuffle(rom_eligible_items)

    replacement_items = list(new_items)
    random.shuffle(replacement_items)
    
    use_cost_criterion = True

    for idx in rom_eligible_items:
        target_cost = ReadItemCost(filebytes, idx)
        replacement_eligible_items = [itm for itm in replacement_items \
            if GetCSVItemAllowedByArmorSimilarityCriterion(itm, helm_x_values, armor_x_values, glove_x_values, shoe_x_values, 3)\
            and ((not use_cost_criterion) or ((itm['Cost'] > target_cost * 0.5) and (itm['Cost'] < target_cost * 1.5)))]
        if use_cost_criterion and (len(replacement_eligible_items) == 0):
            # try again without cost criterion
            replacement_eligible_items = [itm for itm in replacement_items \
                if GetCSVItemAllowedByArmorSimilarityCriterion(itm, helm_x_values, armor_x_values, glove_x_values, shoe_x_values, 3)]
        chosen_item = PickRandomItemFromCSVItems(replacement_eligible_items)
        if chosen_item is None:
            chosen_item = GetItemWithClosestCost(replacement_items, ReadItemCost(filebytes, idx))
        if chosen_item is not None:
            WriteCSVItemToSlot(filebytes, idx, chosen_item)
            AddArmorCSVItemXValueToExisting(chosen_item, helm_x_values, armor_x_values, glove_x_values, shoe_x_values)
            replacement_item_idx = replacement_items.index(chosen_item)
            del(replacement_items[replacement_item_idx])
        else:
            raise Exception("Failed to replace item!")
    return

def PickRandomItemFromCSVItems(csv_eligible_items):
    chosen_item = None
    if len(csv_eligible_items) > 0:
        # print(len(csv_eligible_items))
        random.shuffle(csv_eligible_items)
        total_weight = sum([float(itm['Weight']) for itm in csv_eligible_items])
        pick = random.uniform(0, total_weight)
        chosen_item = None
            
        for item in csv_eligible_items:
            item_weight = float(item['Weight'])
            if pick > item_weight:
                # print(item['Name'], "item weight", item_weight, "remaining pick", pick, "- NOT choosing item")
                pick -= item_weight
            else:
                # print(item['Name'], "item weight", item_weight, "remaining pick", pick, "- choosing item")
                chosen_item = item
                break
                    
        if chosen_item is None:
            raise Exception("Trying to replace " + ReadItemName(filebytes, idx) + ": failed to pick from eligible items!")
    return chosen_item

def GetItemWithClosestCost(csv_items, target_g_value):
    closest_cost_difference = 9999999
    closest_value_csv_item_idx = -1
    csv_item_idx_offset = random.randrange(0, len(csv_items))
    for i in range(0, len(csv_items)):
        csv_item_idx = (i + csv_item_idx_offset) % (len(csv_items))
        csv_item = csv_items[csv_item_idx]
        g_cost_str = csv_item['Cost']
        g_cost = int(g_cost_str)

        cost_difference = abs(target_g_value - g_cost)
        if cost_difference < closest_cost_difference:
            closest_cost_difference = cost_difference
            closest_value_csv_item_idx = csv_item_idx
                        
    if closest_value_csv_item_idx > -1:
        # Found suitable item
        return csv_items[closest_value_csv_item_idx]
    return None

    
def AdjustWeightsByCostRange(cost_ranges, old_items, new_items):
    # Within each cost range, adjust weights of old and new items to result in the same total weight for the cost range,
    # while preserving the relative weights of items
    for cost_range in cost_ranges:
        total_weight = sum([d['Weight'] for d in old_items if d['Cost'] >= cost_range[0] and d['Cost'] <= cost_range[1]])
        if total_weight == 0:
            raise Exception("No old items in cost range " + str(cost_range[0]) + "-" + str(cost_range[1]))
        weight_sum_all_items = total_weight + sum([d['Weight'] for d in new_items if d['Cost'] >= cost_range[0] and d['Cost'] <= cost_range[1]])
        # print("cost range", cost_range, "total weight old items", total_weight, "total weight all items", weight_sum_all_items)
        if (weight_sum_all_items) == 0:
            raise Exception("No items in cost range " + str(cost_range[0]) + "-" + str(cost_range[1]))
        itm_lists = [old_items, new_items]
        for itm_list in itm_lists:
            for itm in itm_list:
                if itm['Cost'] >= cost_range[0] and itm['Cost'] <= cost_range[1]:
                    this_item_weight_proportion = float(itm['Weight']) / (weight_sum_all_items)
                    itm['Weight'] = this_item_weight_proportion * total_weight
                    # print(itm['Name'], itm['Weight'])
    return

    
def ReadItemToDict(filebytes, idx):
    used_by_chrs_str = "FALSE"
    if(IsAbilUsedByEnemies(filebytes, idx)):
        used_by_chrs_str = "TRUE"
    
    old_item = { 'ID':idx, 'Name':ReadItemName(filebytes, idx), 'Uses':ReadItemUses(filebytes, idx), 'Cost':ReadItemCost(filebytes, idx), \
        'FlagsA': ReadItemFlagsA(filebytes, idx), 'FlagsB':ReadItemFlagsB(filebytes, idx), 'Type':ReadItemType(filebytes, idx), \
        'AltUses':ReadItemAltUses(filebytes, idx), 'X':ReadItemX(filebytes, idx), 'Y':ReadItemY(filebytes, idx), \
        'GFX':ReadItemGFX(filebytes, idx), 'Group':ReadItemGroupFlag(filebytes, idx), 'SFX':ReadItemSFX(filebytes, idx), \
        'UsedByChrs':used_by_chrs_str, 'Weight':1, 'New':"FALSE" }
        
    return old_item
    
    
def GenerateHelms(new_items):
    prices = [40, 175, 600, 6000, 20000, 100, 280, 420, 820, 1100, 1440, 1860, 2375, 3000, 3800, 4800, 7500, 9500, 12000, 15500]
    xs = [3, 5, 8, 17, 22, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21]
    GenerateDefenseEquipment(prices, xs, 4, "@", new_items)
    return

def GenerateArmors(new_items):
    prices = [80, 300, 2500, 8500, 109, 177, 275, 598, 846, 1170, 1586, 2771, 3583, 4576, 5779, 7222]
    xs = [4, 8, 13, 19, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 17, 18]
    GenerateDefenseEquipment(prices, xs, 8, "&", new_items)
    return
    
def GenerateGloves(new_items):
    prices = [12, 150, 500, 5000, 10000, 43, 3000, 5680, 6354, 6973, 7549, 8091, 8603, 9092, 9559]
    xs = [1, 3, 4, 6, 15, 2, 5, 7, 8, 9, 10, 11, 12, 13, 14]
    GenerateDefenseEquipment(prices, xs, 16, "*", new_items)
    return
    
def GenerateShoes(new_items):
    prices = [24, 2060, 10480, 23200, 127, 407, 1000, 3830, 6500, 15887, 32902, 45314, 60964]
    xs = [2, 6, 9, 11, 3, 4, 5, 7, 8, 10, 12, 13, 14]
    GenerateDefenseEquipment(prices, xs, 32, "~", new_items)
    return

def GenerateDefenseEquipment(prices, xs, base_flag, name_prefix, new_items):
    for i in range(0, len(prices)):
        flags_vals = [base_flag, base_flag + 64]
        flags_names = ["", ">"]
        element_vals = [0, 15, 64, 56, 255]
        elements_names = ["", "DMG", "WPN", "CHG", "ALL"]
        resist_g_multipliers = [1, 1.5, 2.2, 1.4, 3.0]

        for flag_idx in range(0, len(flags_vals)):
            num_elements = len(element_vals)
            start_element = 0
            if flag_idx == 0:
                num_elements = 1
            else:
                start_element = 1
            for element_idx in range(start_element, num_elements):
                cost = prices[i]
                if (flag_idx == 1) and ((element_idx == 2) or (element_idx == 4)):
                    cost += 5000 # extra cost for O WEAPON
                if flag_idx == 1:
                    cost = int(cost * resist_g_multipliers[element_idx])
                weight = 0.4
                if flag_idx > 0:
                    weight = 0.15
                new_item = { 'ID':-999, 'Uses':254, 'FlagsB':0, 'Type':0, 'AltUses':254, 'GFX':0, 'Group':0, 'SFX':0, 'UsedByChrs':"FALSE", 'Weight':weight, 'New':"TRUE" }
                new_item['Name'] = name_prefix + str(xs[i]) + flags_names[flag_idx] + elements_names[element_idx]
                new_item['Cost'] = cost
                new_item['FlagsA'] = flags_vals[flag_idx]
                new_item['X'] = xs[i]
                new_item['Y'] = element_vals[element_idx]
                
                new_items.append(new_item)

        raise_vals = [1, 2, 3, 4]
        raise_names = ["S", "A", "M", "SA"]
        raise_g_add = [1000, 1000, 2000, 2000]
        for raise_idx in range(0, len(raise_vals)):
            cost = prices[i]
            cost += raise_g_add[raise_idx]
            
            new_item = { 'ID':-999, 'Uses':254, 'FlagsB':0, 'Type':0, 'AltUses':254, 'GFX':0, 'Group':0, 'SFX':0, 'UsedByChrs':"FALSE", 'Weight':0.1, 'New':"TRUE" }

            new_item['Name'] = name_prefix + str(xs[i]) + raise_names[raise_idx]
            new_item['Cost'] = cost
            new_item['FlagsA'] = base_flag
            new_item['X'] = xs[i]
            new_item['Y'] = raise_vals[raise_idx]
            
            new_items.append(new_item)
            
    return
    
def RandomizeCombatItems(filebytes):
    new_items = []
    GenerateStrikeAWeapons(new_items, 1.0)
    GenerateStrikeMWeapons(new_items, 1.0)
    GenerateStrikeSWeapons(new_items, 1.0)
    GenerateCritWeapons(new_items, 0.5)
    GenerateBows(new_items, 0.3)
    GenerateGuns(new_items, 0.3)
    GenerateWhips(new_items, 0.2)
    GenerateOrdnances(new_items, 0.3)
    GenerateAttackSpells(new_items, 0.4)
    old_items = []
    for idx in range(0x00, 0x80):
        if idx in [0x11, 0x12, 0x13, 0x23]: # KING items, BATTLE sword
            continue
        tp = ReadItemType(filebytes, idx)
        if not tp in weapon_types:
            continue
        if IsAbilUsedByEnemies(filebytes, idx):
            continue
        old_items.append(ReadItemToDict(filebytes, idx))
        
    reuse_item_types = [5, 9, 13, 14, 15, 16, 21, 22, 23, 3, 4, 27, 28, 29]
    new_items = new_items + [itm for itm in old_items if (int(itm['Type']) in reuse_item_types)]
                
    cost_ranges = [[0, 70], [71, 200], [201, 500], [501, 2500], [2501, 5000], [5001, 10000], [10001, 20000], [20001, 9999999]]
    AdjustWeightsByCostRange(cost_ranges, old_items, new_items)
    
    type_group_map = { 6:6, 7:6, 8:6 } # group Strike (S), Critical (T) and Critical (E) together
    for t in weapon_types:
        if not t in type_group_map.keys():
            type_group_map[t] = t
    
    group_value_differences = { 6:3, 11:3, 12:3, 18:50, 17:50, 19:30, 20:30, 26:2 }
    for g in type_group_map.values():
        if not g in group_value_differences:
            group_value_differences[g] = 0
    group_values = dict()
    for group in type_group_map.values():
        group_values[group] = []
    
    rom_eligible_items = [d['ID'] for d in old_items]
    random.shuffle(rom_eligible_items)

    replacement_items = list(new_items)
    random.shuffle(replacement_items)
    
    use_cost_criterion = True

    for idx in rom_eligible_items:
        target_cost = ReadItemCost(filebytes, idx)
        replacement_eligible_items = [itm for itm in replacement_items \
            if GetCSVItemAllowedByTypeSimilarityCriterion(itm, type_group_map, group_values, group_value_differences)\
                and ((not use_cost_criterion) or ((itm['Cost'] > target_cost * 0.5) and (itm['Cost'] < target_cost * 1.5)))]
        if use_cost_criterion and (len(replacement_eligible_items) == 0):
            # try again without cost criterion
            replacement_eligible_items = [itm for itm in replacement_items \
                if GetCSVItemAllowedByTypeSimilarityCriterion(itm, type_group_map, group_values, group_value_differences)]
        chosen_item = PickRandomItemFromCSVItems(replacement_eligible_items)
        if chosen_item is None:
            chosen_item = GetItemWithClosestCost(replacement_items, ReadItemCost(filebytes, idx))
        if chosen_item is not None:
            WriteCSVItemToSlot(filebytes, idx, chosen_item)
            AddCSVItemXValueToExisting(chosen_item, type_group_map, group_values)
            replacement_item_idx = replacement_items.index(chosen_item)
            del(replacement_items[replacement_item_idx])
        else:
            raise Exception("Failed to replace item!")
            
    # Rewrite names of equipment that wasn't replaced to fit our naming scheme
    if ReadItemName(filebytes, 0x23) == "$BATTLE":
        WriteItemName(filebytes, 0x23, "$S5")
    if ReadItemName(filebytes, 0x2b) == "$ICE   ":
        WriteItemName(filebytes, 0x2b, "$S10ICE")
    if (ReadItemName(filebytes, 0x46) == "BALKAN ") or (ReadItemName(filebytes, 0x46) == "VULCAN "):
        WriteItemName(filebytes, 0x46, "O200")
    
    return
    
def GenerateStrikeAWeapons(new_items, weight_multiplier):
    prices = [24, 2060, 10480, 23200, 127, 407, 1000, 3830, 6500, 15887, 32902, 45314, 60964]
    xs = [2, 6, 9, 11, 3, 4, 5, 7, 8, 10, 12, 13, 14]
    tp = 0x0B
    name_prefix = "$A"
    GenerateStrikeWeapons(tp, prices, xs, name_prefix, weight_multiplier, new_items)
    return
    
def GenerateStrikeMWeapons(new_items, weight_multiplier):
    prices = [24, 2060, 10480, 23200, 127, 407, 1000, 3830, 6500, 15887, 32902, 45314, 60964]
    xs = [2, 6, 9, 11, 3, 4, 5, 7, 8, 10, 12, 13, 14]
    tp = 0x0C
    name_prefix = "$M"
    GenerateStrikeWeapons(tp, prices, xs, name_prefix, weight_multiplier, new_items)
    return

def GenerateStrikeSWeapons(new_items, weight_multiplier):
    prices = [24, 2060, 10480, 23200, 127, 407, 1000, 3830, 6500, 15887, 32902, 45314, 60964]
    xs = [2, 6, 9, 11, 3, 4, 5, 7, 8, 10, 12, 13, 14]
    tp = 0x06
    name_prefix = "$S"
    GenerateStrikeWeapons(tp, prices, xs, name_prefix, weight_multiplier, new_items)
    return

def GenerateStrikeWeapons(tp, prices, xs, name_prefix, weight_multiplier, new_items):
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]), 'Uses':50, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':160, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':0, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.21 * weight_multiplier, 'New':"TRUE" })
        # Runic variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RNC", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':168, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':0, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Defend variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "DEF", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':161, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':50, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Runic and defend variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RD", 'Uses':50, 'Cost':int(prices[i]*1.1), 'FlagsA':1, 'FlagsB':169, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':50, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Fire skin variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "FSK", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':176, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':1, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Ice skin variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "ISK", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':176, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':2, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Elec skin variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "ESK", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':176, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':4, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Poison skin variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "PSK", 'Uses':50, 'Cost':int(prices[i]*1.05), 'FlagsA':1, 'FlagsB':176, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':8, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.11 * weight_multiplier, 'New':"TRUE" })
        # Revenge variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RVG", 'Uses':50, 'Cost':int(prices[i]*1.5) + 50000, 'FlagsA':1, 'FlagsB':162, \
            'Type':tp, 'AltUses':50, 'X':xs[i], 'Y':0, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.053 * weight_multiplier, 'New':"TRUE" })
    return
    
def GenerateCritWeapons(new_items, weight_multiplier):
    prices = [24, 2060, 10480, 23200, 127, 407, 1000, 3830, 6500, 15887, 32902, 45314, 60964]
    xs = [2, 6, 9, 11, 3, 4, 5, 7, 8, 10, 12, 13, 14]
    name_prefix = "$S"
    for i in range(0, len(prices)):
        # Coral (CRL)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "CRL", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':8, 'AltUses':50, 'X':xs[i], 'Y':1, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # Ogre (OGR)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "OGR", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':8, 'AltUses':50, 'X':xs[i], 'Y':2, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # Dragon (DGN)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "DGN", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':8, 'AltUses':50, 'X':xs[i], 'Y':4, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # Unholy (SUN)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "SUN", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':8, 'AltUses':50, 'X':xs[i], 'Y':8, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # All classes (CLS)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "CLS", 'Uses':50, 'Cost':int(prices[i] * 1.1), 'FlagsA':1, 'FlagsB':160, \
            'Type':8, 'AltUses':50, 'X':xs[i], 'Y':15, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.0625 * weight_multiplier, 'New':"TRUE" })
        # Fire (FLM)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "FLM", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':7, 'AltUses':50, 'X':xs[i], 'Y':1, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # Ice (ICE)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "ICE", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':7, 'AltUses':50, 'X':xs[i], 'Y':2, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # Elec (ELC)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "ELC", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':160, \
            'Type':7, 'AltUses':50, 'X':xs[i], 'Y':4, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.125 * weight_multiplier, 'New':"TRUE" })
        # "King" (all elements) (KNG)
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "KNG", 'Uses':50, 'Cost':int(prices[i] * 1.1), 'FlagsA':1, 'FlagsB':160, \
            'Type':7, 'AltUses':50, 'X':xs[i], 'Y':255, 'GFX':1, 'Group':0, 'SFX':0x18, 'UsedByChrs':"FALSE", 'Weight':0.0625 * weight_multiplier, 'New':"TRUE" })
    return
    
def GenerateBows(new_items, weight_multiplier):
    prices = [50, 8000, 32000, 84, 138, 228, 375, 619, 1020, 1681, 2772, 4571, 12424, 20484, 55681]
    xs = [20, 120, 150, 30, 40, 50, 60, 70, 80, 90, 100, 110, 130, 140, 160]
    ys = [33, 41, 58, 33, 34, 34, 34, 35, 35, 36, 38, 39, 46, 51, 70]
    name_prefix = "B"
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]), 'Uses':50, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':18, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':2, 'Group':0, 'SFX':19, 'UsedByChrs':"FALSE", 'Weight':0.7 * weight_multiplier, 'New':"TRUE" })
        # Runic variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RNC", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':136, \
            'Type':18, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':2, 'Group':0, 'SFX':19, 'UsedByChrs':"FALSE", 'Weight':0.2 * weight_multiplier, 'New':"TRUE" })
        # Revenge variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RVG", 'Uses':50, 'Cost':int(prices[i] * 1.5) + 50000, 'FlagsA':1, 'FlagsB':130, \
            'Type':18, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':2, 'Group':0, 'SFX':19, 'UsedByChrs':"FALSE", 'Weight':0.1 * weight_multiplier, 'New':"TRUE" })
    return
    
def GenerateGuns(new_items, weight_multiplier):
    prices = [80, 800, 8000, 113, 140, 174, 217, 270, 335, 519, 802, 997, 1240, 1543, 1918, 2386, 2967, 3689, 4588, 5706, 7096]
    xs = [40, 130, 250, 50, 60, 70, 80, 90, 100, 120, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240]
    ys = [35, 46, 65, 36, 37, 38, 40, 41, 42, 45, 48, 49, 51, 53, 54, 56, 58, 59, 61, 63, 65]
    name_prefix = "^"
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]), 'Uses':30, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':17, 'AltUses':30, 'X':xs[i], 'Y':ys[i], 'GFX':3, 'Group':0, 'SFX':20, 'UsedByChrs':"FALSE", 'Weight':0.7 * weight_multiplier, 'New':"TRUE" })
        # Runic variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RNC", 'Uses':30, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':136, \
            'Type':17, 'AltUses':30, 'X':xs[i], 'Y':ys[i], 'GFX':3, 'Group':0, 'SFX':20, 'UsedByChrs':"FALSE", 'Weight':0.2 * weight_multiplier, 'New':"TRUE" })
        # Revenge variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RVG", 'Uses':30, 'Cost':int(prices[i] * 1.5) + 50000, 'FlagsA':1, 'FlagsB':130, \
            'Type':17, 'AltUses':30, 'X':xs[i], 'Y':ys[i], 'GFX':3, 'Group':0, 'SFX':20, 'UsedByChrs':"FALSE", 'Weight':0.1 * weight_multiplier, 'New':"TRUE" })
    return

def GenerateWhips(new_items, weight_multiplier):
    prices = [80, 800, 213, 361, 2499, 7185, 20656]
    xs = [15, 70, 30, 45, 100, 130, 160]
    ys = [67, 51, 63, 57, 49, 48, 47]
    name_prefix = "W"
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]), 'Uses':50, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':160, \
            'Type':19, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':1, 'Group':0, 'SFX':30, 'UsedByChrs':"FALSE", 'Weight':0.7 * weight_multiplier, 'New':"TRUE" })
        # Runic variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RNC", 'Uses':50, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':168, \
            'Type':19, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':1, 'Group':0, 'SFX':30, 'UsedByChrs':"FALSE", 'Weight':0.2 * weight_multiplier, 'New':"TRUE" })
        # Revenge variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RVG", 'Uses':50, 'Cost':int(prices[i] * 1.5) + 50000, 'FlagsA':1, 'FlagsB':162, \
            'Type':19, 'AltUses':50, 'X':xs[i], 'Y':ys[i], 'GFX':1, 'Group':0, 'SFX':30, 'UsedByChrs':"FALSE", 'Weight':0.1 * weight_multiplier, 'New':"TRUE" })
    return

def GenerateOrdnances(new_items, weight_multiplier):
    prices = [400, 800, 4000, 8000, 130, 145, 202, 601, 1789, 5328, 27384]
    xs = [50, 100, 150, 200, 5, 10, 25, 75, 125, 175, 250]
    ys = [25, 50, 100, 150, 5, 5, 10, 50, 100, 150, 200]
    gfxs = [10, 9, 9, 10, 10, 10, 10, 10, 10, 9, 9]
    sfxs = [13, 5, 5, 13, 13, 13, 13, 13, 13, 5, 5]
    name_prefix = "O"
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':20, 'AltUses':20, 'X':xs[i], 'Y':ys[i], 'GFX':gfxs[i], 'Group':128, 'SFX':sfxs[i], 'UsedByChrs':"FALSE", 'Weight':0.7 * weight_multiplier, 'New':"TRUE" })
        # Runic variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RNC", 'Uses':20, 'Cost':int(prices[i] * 1.05), 'FlagsA':1, 'FlagsB':136, \
            'Type':20, 'AltUses':20, 'X':xs[i], 'Y':ys[i], 'GFX':gfxs[i], 'Group':128, 'SFX':sfxs[i], 'UsedByChrs':"FALSE", 'Weight':0.2 * weight_multiplier, 'New':"TRUE" })
        # Revenge variant
        new_items.append({ 'ID':-999, 'Name':name_prefix + str(xs[i]) + "RVG", 'Uses':20, 'Cost':int(prices[i] * 1.5) + 50000, 'FlagsA':1, 'FlagsB':130, \
            'Type':20, 'AltUses':20, 'X':xs[i], 'Y':ys[i], 'GFX':gfxs[i], 'Group':128, 'SFX':sfxs[i], 'UsedByChrs':"FALSE", 'Weight':0.1 * weight_multiplier, 'New':"TRUE" })
    return
    
def GenerateAttackSpells(new_items, weight_multiplier):
    prices = [500, 1000, 2000, 5000, 10000, 30000]
    xs = [5, 6, 7, 8, 9, 10]
    name_prefix = "%"
    for i in range(0, len(prices)):
        new_items.append({ 'ID':-999, 'Name':name_prefix + "FIR" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':1, 'GFX':7, 'Group':128, 'SFX':12, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "FIRA" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':1, 'GFX':7, 'Group':0, 'SFX':12, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })
        
        new_items.append({ 'ID':-999, 'Name':name_prefix + "ICE" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':2, 'GFX':8, 'Group':128, 'SFX':34, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "TRND" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':2, 'GFX':80, 'Group':0, 'SFX':36, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })
        
        new_items.append({ 'ID':-999, 'Name':name_prefix + "ELC" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':4, 'GFX':6, 'Group':128, 'SFX':33, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "ELCA" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':4, 'GFX':6, 'Group':0, 'SFX':33, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })

        new_items.append({ 'ID':-999, 'Name':name_prefix + "FOG" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':8, 'GFX':13, 'Group':128, 'SFX':28, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "ACID" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':8, 'GFX':64, 'Group':0, 'SFX':4, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })

        new_items.append({ 'ID':-999, 'Name':name_prefix + "QUK" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':0x80, 'GFX':32, 'Group':128, 'SFX':31, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "QUKA" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':0x80, 'GFX':32, 'Group':0, 'SFX':31, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })

        new_items.append({ 'ID':-999, 'Name':name_prefix + "FRC" + str(xs[i]), 'Uses':20, 'Cost':prices[i], 'FlagsA':1, 'FlagsB':128, \
            'Type':26, 'AltUses':20, 'X':xs[i], 'Y':0, 'GFX':156, 'Group':128, 'SFX':2, 'UsedByChrs':"FALSE", 'Weight':0.15 * weight_multiplier, 'New':"TRUE" })
        new_items.append({ 'ID':-999, 'Name':name_prefix + "FLAR" + str(xs[i]), 'Uses':20, 'Cost':prices[i] + 20000, 'FlagsA':1, 'FlagsB':192, \
            'Type':34, 'AltUses':20, 'X':xs[i], 'Y':0x80, 'GFX':156, 'Group':0, 'SFX':2, 'UsedByChrs':"FALSE", 'Weight':0.05 * weight_multiplier, 'New':"TRUE" })
    return

def RewriteNonMonsterEnemyItems(filebytes, character_abils, original_item_details):
    for character_idx in range(0x96, 0xac): # 0x96-0xab are non-monster enemies
        original_race_byte = filebytes[0x0001aae8 + (9 * character_idx)]
        original_num_abilities = len(character_abils[character_idx])
        for abil_idx in range(original_num_abilities - 1, -1, -1):
            abil_id = character_abils[character_idx][abil_idx]
            if abil_id < 0x80: # items are 0x00-0x80
                keep = False
                original_item_type = original_item_details[abil_id]['Type']
                if original_item_type != 0: # type 0 are non-combat - removing them from inventory doesn't affect enemy stats
                    original_item_x = original_item_details[abil_id]['X']
                    type_matches = (original_item_type == ReadItemType(filebytes, abil_id))
                    x_matches = (original_item_x == ReadItemX(filebytes, abil_id))
                    if type_matches and x_matches:
                        keep = True
                    else:
                        # Try to find a replacement
                        original_item_y = original_item_details[abil_id]['Y']
                        x_tolerance = 2
                        if original_item_type in [17, 18, 19, 20]: # Projectiles, whips, ordnance
                            x_tolerance = 30
                        new_item_id = FindClosestItem(filebytes, original_item_type, original_item_x, original_item_y, x_tolerance, 999)
                        if new_item_id > -1:
                            # print("Character", hex(character_idx), "replacing", original_item_details[abil_id]['Name'], "with", ReadItemName(filebytes, new_item_id))
                            keep = True
                            character_abils[character_idx][abil_idx] = new_item_id
                if not keep:
                    del(character_abils[character_idx][abil_idx])
        if len(character_abils[character_idx]) == 0:
            # Must have at least one ability - add a POTION
            character_abils[character_idx].append(0x00)
        final_num_abilities = len(character_abils[character_idx])
        # Write amended value to the race/meat drop/num abils byte
        # print(hex(character_idx), original_race_byte, original_num_abilities)
        filebytes[0x0001aae8 + (9 * character_idx)] = (original_race_byte - (8 * (original_num_abilities - 1))) + (8 * (final_num_abilities - 1))
    return
    
def FindClosestItem(filebytes, itm_type, itm_x, itm_y, x_tolerance, y_tolerance):
    closest_score = 999999999
    closest_idx = -1
    for idx in range(0x00, 0x80):
        new_item_type = ReadItemType(filebytes, idx)
        new_item_x = ReadItemX(filebytes, idx)
        new_item_y = ReadItemY(filebytes, idx)
        if new_item_type == itm_type:
            x_diff = abs(new_item_x - itm_x)
            y_diff = abs(new_item_y - itm_y)
            if (x_diff <= x_tolerance) and (y_diff <= y_tolerance):
                score = x_diff + y_diff
                if score < closest_score:
                    closest_score = score
                    closest_idx = idx
    return closest_idx
    
def GetUnusedEquipment(filebytes):
    unused_items = []
    for idx in range(0x00, 0x80):
        used = False
        if idx in story_items:
            used = True
        if IsAbilUsedByEnemies(filebytes, idx):
            used = True
        
        skip_item = True
        if GetItemIsArmor(filebytes, idx):
            skip_item = False
        if skip_item:
            tp = ReadItemType(filebytes, idx)
            if tp in weapon_types:
                skip_item = False
        if skip_item:
            continue
        
        if not used:
            for chest_addr in chest_addrs:
                if filebytes[chest_addr] == idx:
                    used = True
                    break
        
        if not used:
            for shop_idx in range(0, len(equipment_shop_addrs)):
                shop_addr = equipment_shop_addrs[shop_idx]
                for i in range(shop_equipment_start_idx[shop_idx], 10):
                    if filebytes[shop_addr + i] == idx:
                        used = True
                        break
        if not used:
            unused_items.append(idx)
    return unused_items
    
def GetItemIsArmor(filebytes, idx):
    tp = ReadItemType(filebytes, idx)
    if tp != 0:
        return False
    flagsA = ReadItemFlagsA(filebytes, idx)
    if not GetAnyFlagSet(flagsA, armor_flags):
        return False
    return True
    
def RandomizeFirstTowerSection(filebytes):
    first_room = [[0xbb, 0x30, 0x15, 0x0d]]
    remaining_rooms = [[[0x17, 0x02, 0x0a, 0x0d], [0x18, 0x02, 0x13, 0x0a]], \
        [[0x35, 0x03, 0x1d, 0x1a], [0x036, 0x03, 0x0a, 0x0d], [0x037, 0x03, 0x12, 0x1b]], \
        [[0x058, 0x04, 0x14, 0x0d], [0x059, 0x04, 0x1b, 0x1c], [0x05A, 0x04, 0x0c, 0x1d]], \
        [[0x05C, 0x05, 0x14, 0x0c]], \
        [[0x0bc, 0x31, 0x15, 0x14], [0x0bd, 0x31, 0x15, 0x0D]], \
        [[0x0be, 0x32, 0x15, 0x14], [0x0bf, 0x32, 0x15, 0x0D]], \
        [[0x0c0, 0x33, 0x15, 0x14], [0x0c1, 0x33, 0x15, 0x0D]], \
        [[0x0e9, 0x4a, 0x0d, 0x12]], \
        [[0x0ea, 0x4B, 0x09, 0x10]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)
    return
    
def RandomizeSecondTowerSection(filebytes):
    first_room = [[0x05b, 0x05, 0x19, 0x16]]
    remaining_rooms = [[[0x03a, 0x06, 0x13, 0x1d], [0x03b, 0x06, 0x19, 0x14]], \
        [[0x05e, 0x07, 0x09, 0x19], [0x05f, 0x07, 0x13, 0x1c], [0x060, 0x07, 0x13, 0x0d]], \
        [[0x04d, 0x08, 0x1e, 0x19], [0x04e, 0x08, 0x09, 0x18]], \
        [[0x061, 0x09, 0x0a, 0x0d], [0x062, 0x09, 0x1f, 0x18], [0x063, 0x09, 0x18, 0x0d]], \
        [[0x065, 0x0a, 0x0a, 0x0c]], \
        [[0x0c2, 0x34, 0x33, 0x14], [0x0c3, 0x34, 0x33, 0x0d]], \
        [[0x0c4, 0x35, 0x33, 0x14], [0x0c5, 0x35, 0x33, 0x0d]], \
        [[0x0c6, 0x36, 0x33, 0x14], [0x0c7, 0x36, 0x33, 0x0d]], \
        [[0x0c8, 0x37, 0x33, 0x14], [0x0c9, 0x37, 0x33, 0x0d]], \
        [[0x0ca, 0x38, 0x33, 0x14], [0x0cb, 0x38, 0x33, 0x0d]], \
        [[0x0eb, 0x4c, 0x15, 0x23]], \
        [[0x0ec, 0x4d, 0x13, 0x0c]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)
    return

def RandomizeThirdTowerSection(filebytes):
    first_room = [[0x064, 0x0a, 0x14, 0x0d]]
    
    # These rooms don't include the exits to the flooded/dry worlds on 13f and 14f,
    # because they have multiple exits, including the one-way exit from 14f to 13f
    # when you remove the garbage from the bottom of the lake. So they won't be randomized,
    # and will remain connected to 13f and 14f in the same way as the vanilla game.
    remaining_rooms = [[[0x067, 0x0b, 0x0a, 0x0f], [0x068, 0x0b, 0x1d, 0x0e]], \
        [[0x069, 0x0c, 0x1b, 0x0b], [0x06a, 0x0c, 0x0a, 0x0c], [0x06b, 0x0c, 0x09, 0x19]], \
        [[0x06c, 0x0d, 0x17, 0x0b], [0x06d, 0x0d, 0x1c, 0x18]], \
        [[0x070, 0x0e, 0x08, 0x17], [0x071, 0x0e, 0x1b, 0x0c]], \
        [[0x074, 0x0f, 0x10, 0x0b], [0x075, 0x0f, 0x08, 0x16]], \
        [[0x077, 0x10, 0x0e, 0x0a]], \
        [[0x0cc, 0x39, 0x15, 0x14], [0x0cd, 0x39, 0x15, 0x0d]], \
        [[0x0ce, 0x3a, 0x15, 0x14], [0x0cf, 0x3a, 0x15, 0x0d]], \
        [[0x0d0, 0x3b, 0x15, 0x14], [0x0d1, 0x3b, 0x15, 0x0d]], \
        [[0x0d2, 0x3c, 0x15, 0x14], [0x0d3, 0x3c, 0x15, 0x0d]], \
        [[0x0d4, 0x3d, 0x15, 0x14], [0x0d5, 0x3d, 0x15, 0x0d]], \
        [[0x0d6, 0x3e, 0x15, 0x14], [0x0d7, 0x3e, 0x15, 0x0d]], \
        [[0x0ed, 0x4e, 0x20, 0x10]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)
    return

def RandomizeFourthTowerSection(filebytes):
    first_room = [[0x076, 0x10, 0x11, 0x16]]
    
    # These rooms include the connection between the flower world on 21f and the hut,
    # so you might have to go through the hut to continue up the tower!
    remaining_rooms = [[[0x07b, 0x11, 0x0b, 0x0b], [0x07c, 0x11, 0x0b, 0x19]], \
        [[0x07d, 0x12, 0x17, 0x16], [0x07e, 0x12, 0x11, 0x0b], [0x07f, 0x12, 0x0b, 0x16]], \
        [[0x080, 0x13, 0x19, 0x0a], [0x081, 0x13, 0x15, 0x12], [0x082, 0x13, 0x06, 0x0f]], \
        [[0x083, 0x14, 0x16, 0x19], [0x084, 0x14, 0x1b, 0x0c], [0x085, 0x14, 0x09, 0x19]], \
        [[0x086, 0x15, 0x0b, 0x0e], [0x087, 0x15, 0x18, 0x1c], [0x088, 0x15, 0x13, 0x14]], \
        [[0x08a, 0x16, 0x07, 0x08]], \
        [[0x0d8, 0x3f, 0x33, 0x14], [0x0d9, 0x3f, 0x33, 0x0d]], \
        [[0x0da, 0x40, 0x33, 0x14], [0x0db, 0x40, 0x33, 0x0d]], \
        [[0x0dc, 0x41, 0x33, 0x14], [0x0dd, 0x41, 0x33, 0x0d]], \
        [[0x0de, 0x42, 0x33, 0x14], [0x0df, 0x42, 0x33, 0x0d]], \
        [[0x0e0, 0x43, 0x33, 0x14], [0x0e1, 0x43, 0x33, 0x0d]], \
        [[0x0e2, 0x44, 0x33, 0x14], [0x0e3, 0x44, 0x33, 0x0d]], \
        [[0x0f0, 0x51, 0x0f, 0x0f]], \
        [[0x0f1, 0x52, 0x0b, 0x0a]], \
        [[0x0f3, 0x53, 0x07, 0x0d]], \
        [[0x0f4, 0x54, 0x10, 0x17], [0x0f5, 0x54, 0x21, 0x0c]], \
        [[0x0f9, 0x57, 0x22, 0x26]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)
    return

def RandomizeTowerSection(filebytes, first_room_param, remaining_rooms_param):
    
    # Each room is a list of exits, and each exit is a list with four data members, defined as follows:
    # [0] is exit offset
    # [1] is room ID for return
    # [2] is X coordinate for return
    # [3] is Y coordinate for return
    
    # Deep copy data
    first_room = []
    for ext in first_room_param:
        first_room.append(list(ext))
    remaining_rooms = []
    for room in remaining_rooms_param:
        new_room = []
        for ext in room:
            new_room.append(list(ext))
        remaining_rooms.append(new_room)
    
    open_exits = list(first_room)
    exit_pairs = []
    
    # (1) First, randomly connect rooms with more than two exits - connect one exit from each room
    
    rooms_to_connect = []
    for i in range(len(remaining_rooms) - 1, -1, -1):
        if len(remaining_rooms[i]) > 2:
            rooms_to_connect.append(remaining_rooms[i])
            del(remaining_rooms[i])
            
    for room in rooms_to_connect:
        room_exit_idx = random.randrange(0, len(room))
        open_exit_idx = random.randrange(0, len(open_exits))
        exit_pairs.append([room[room_exit_idx], open_exits[open_exit_idx]])
        del(room[room_exit_idx])
        del(open_exits[open_exit_idx])
        for remaining_exit in room:
            open_exits.append(remaining_exit)
        
    # (2) Randomly connect rooms with one exit
    
    rooms_to_connect = []
    for i in range(len(remaining_rooms) - 1, -1, -1):
        if len(remaining_rooms[i]) == 1:
            rooms_to_connect.append(remaining_rooms[i])
            del(remaining_rooms[i])
            
    for room in rooms_to_connect:
        open_exit_idx = random.randrange(0, len(open_exits))
        exit_pairs.append([room[0], open_exits[open_exit_idx]])
        del(open_exits[open_exit_idx])
        
    # Sanity check: the number of open exits should be even
    if len(open_exits) % 2 != 0:
        raise Exception("Should be an even number of exits but there are " + str(len(open_exits)))
        
    # (3) Randomly connect open exits together, ensuring we don't connect two exits from the same room
    
    while len(open_exits) > 0:
        # Sanity check: the exits should be in different rooms
        if all(open_exit[1] == open_exits[0][1] for open_exit in open_exits):
            raise Exception("All remaining exits are in the same room!")

        # Pick two open exits which don't come from the same room (member [1])
        first_open_exit_idx = random.randrange(0, len(open_exits))
        second_open_exit_idx = first_open_exit_idx
        while (second_open_exit_idx == first_open_exit_idx) or (open_exits[first_open_exit_idx][1] == open_exits[second_open_exit_idx][1]):
            second_open_exit_idx = random.randrange(0, len(open_exits))

        exit_pairs.append([open_exits[first_open_exit_idx], open_exits[second_open_exit_idx]])

        # Remove the exits from the list - the higher index has to be removed first so the lower index will still be correct
        delete_indices = [first_open_exit_idx, second_open_exit_idx]
        delete_indices.sort(reverse=True)
        for delete_index in delete_indices:
            del(open_exits[delete_index])
        
    # Sanity check: this should leave no open exits
    if len(open_exits) > 0:
        raise Exception("Should be no open exits but found " + str(len(open_exits)))
        
    # (4) Finally, randomly insert rooms with two exits between previous connections
    
    rooms_to_connect = []
    # Sanity check
    for i in range(len(remaining_rooms) - 1, -1, -1):
        if len(remaining_rooms[i]) != 2:
            raise Exception("Unexpectedly found room with " + str(len(remaining_rooms[i])) + " exits!")
    rooms_to_connect = remaining_rooms
    
    for i in range(0, len(rooms_to_connect)):
        room = rooms_to_connect[i]
        existing_exit_pair_idx = random.randrange(0, len(exit_pairs))
        exit_pair = exit_pairs[existing_exit_pair_idx]
        first_room_exit = 0
        second_room_exit = 1
        if random.randrange(0, 2) == 0:
            first_room_exit = 1
            second_room_exit = 0
        exit_pairs.append([room[first_room_exit], exit_pair[0]])
        exit_pairs.append([room[second_room_exit], exit_pair[1]])
        del(exit_pairs[existing_exit_pair_idx])
    
    # Write data
    WriteExitPairs(filebytes, exit_pairs)
    
    # for pair in exit_pairs:
    #    print([str(hex(a)) for a in pair[0]], [str(hex(a)) for a in pair[1]])

    return
    
def WriteExitPairs(filebytes, exit_pairs):
    for pair in exit_pairs:
        for i in range(0, 3):
            if pair[0][0] >= 0:
                # Copy the three bytes from pair[1][1:4] to the offset specified by pair[0][0]
                filebytes[0x92d0 + (3 * pair[0][0]) + i] = pair[1][i + 1]
            if pair[1][0] >= 0:
                # Copy the three bytes from pair[0][1:4] to the offset specified by pair[1][0]
                filebytes[0x92d0 + (3 * pair[1][0]) + i] = pair[0][i + 1]
    return
    
def RandomizeOceanCaves(filebytes):
    # Exit pairs for first cave system
    exit_pairs_1 = [[[0x11d, 0x66, 0x12, 0x30], [0x126, 0x68, 0x07, 0x18]], \
        [[0x11e, 0x66, 0x12, 0x26], [0x127, 0x68, 0x0d, 0x03]], \
        [[0x11f, 0x66, 0x17, 0x2a], [0x128, 0x68, 0x1b, 0x03]], \
        [[0x120, 0x66, 0x19, 0x32], [0x129, 0x68, 0x17, 0x12]] \
        ]
    
    # Exit pairs for second cave system
    exit_pairs_2 = [[[0x121, 0x66, 0x1c, 0x27], [0x12a, 0x69, 0x08, 0x2f]], \
        [[0x122, 0x66, 0x1c, 0x1f], [0x12b, 0x69, 0x0b, 0x1e]], \
        [[0x123, 0x66, 0x23, 0x20], [0x12c, 0x69, 0x1a, 0x17]], \
        [[0x124, 0x66, 0x1f, 0x28], [0x12d, 0x69, 0x18, 0x2a]]]
        
    # Within each of the two caves, any of the four exits can be accessed.
    # So we can just randomly permute the exit pairs within each cave
    
    RandomlyPermuteExitPairs(exit_pairs_1)
    RandomlyPermuteExitPairs(exit_pairs_2)
    
    WriteExitPairs(filebytes, exit_pairs_1)
    WriteExitPairs(filebytes, exit_pairs_2)
    
    return
    
def RandomlyPermuteExitPairs(exit_pairs):
    # print("before", exit_pairs)
    pair_second = [list(pair[1]) for pair in exit_pairs]
    random.shuffle(pair_second)
    for idx in range(0, len(pair_second)):
        exit_pairs[idx][1] = pair_second[idx]
    # print("after", exit_pairs)
    return
    
def RandomizeBanditCaveRooms(filebytes):
    one_way_exits = [[0x10d, 0x62, 0x33, 0x0e], [0x111, 0x61, 0x32, 0x1e]]
    RandomlyPermuteOneWayExits(one_way_exits)
    WriteOneWayExits(filebytes, one_way_exits)
    return
    
def RandomizeDragonPalaceRooms(filebytes):
    one_way_exits = [[0x13f, 0x78, 0x16, 0x06], [0x142, 0x77, 0x21, 0x09], [0x145, 0x76, 0x0f, 0x2e]]
    RandomlyPermuteOneWayExits(one_way_exits)
    WriteOneWayExits(filebytes, one_way_exits)
    return
    
def RandomlyPermuteOneWayExits(one_way_exits):
    exit_addrs = [e[0] for e in one_way_exits]
    random.shuffle(exit_addrs)
    for idx in range(0, len(exit_addrs)):
        one_way_exits[idx][0] = exit_addrs[idx]
    return
    
def WriteOneWayExits(filebytes, one_way_exits):
    for ext in one_way_exits:
        addr_offset = ext[0]
        for i in range(0, 3):
            filebytes[0x92d0 + (3 * addr_offset) + i] = ext[i + 1]    
    return
    
def RandomizeUnderseaCave(filebytes):
    exit_pairs = [[[0x136, 0x6f, 0x0d, 0x23], [0x138, 0x70, 0x12, 0x32]], \
        [[0x137, 0x6f, 0x13, 0x23], [0x13a, 0x71, 0x2e, 0x0f]] \
        ]
    RandomlyPermuteExitPairs(exit_pairs)
    WriteExitPairs(filebytes, exit_pairs)
    return
    
def RandomizeRuinsSkyscraper(filebytes):
    first_room = [[0x1a7, 0xa6, 0x10, 0xd], [0x1a8, 0xa6, 0x18, 0x0d], [0x1a6, 0xa6, 0x14, 0x1a]]

    remaining_rooms = [[[-1, 0x48, 0x10, 0x18]], \
        [[-1, 0x9b, 0x10, 0x18]], \
        [[0x1aa, 0xa7, 0xc, 0xf], [0x1ab, 0xa7, 0x1c, 0x0f], [0x1ad, 0xa7, 0x1c, 0x1e], [0x1ac, 0xa7, 0x0c, 0x1e]], \
        [[0x1ae, 0xa8, 0x12, 0x0e], [0x1af, 0xa8, 0x19, 0x13], [0x1b0, 0xa8, 0xb, 0x18], [0x1b1, 0xa8, 0x11, 0x13]], \
        [[0x1b2, 0xa9, 0x3c, 0xf], [0x1b3, 0xa9, 0x2, 0xf]], \
        [[0x1b4, 0xaa, 0xc, 0xe], [0x1b5, 0xaa, 0x10, 0x13], [0x1b6, 0xaa, 0x12, 0x13], [0x1b7, 0xaa, 0x16, 0x17]], \
        [[0x1b8, 0xab, 0xd, 0xe], [0x1b9, 0xab, 0x10, 0x14], [0x1ba, 0xab, 0x17, 0x17], [0x1bb, 0xab, 0x14, 0x12]], \
        [[0x1bd, 0xac, 0xb, 0xe], [0x1bf, 0xac, 0x10, 0x17], [0x1bc, 0xac, 0x11, 0x0e], [0x1be, 0xac, 0x16, 0x0e]], \
        [[-1, 0xad, 0x10, 0x18]], \
        [[-1, 0xad, 0x10, 0x18]], \
        [[-1, 0xad, 0x10, 0x18]], \
        [[-1, 0xae, 0x10, 0x18]], \
        [[-1, 0xae, 0x10, 0x18]], \
        [[-1, 0xae, 0x10, 0x18]], \
        [[-1, 0xaf, 0x10, 0x18]], \
        [[-1, 0xaf, 0x10, 0x18]], \
        [[-1, 0xaf, 0x10, 0x18]], \
        [[0x1c0, 0xb0, 0xf, 0x11], [0x1c1, 0xb0, 0xf, 0x26]], \
        [[0x1c2, 0xb1, 0xf, 0x11], [0x1c3, 0xb1, 0xf, 0x26]], \
        [[0x1c4, 0xb2, 0xf, 0x11], [0x1c5, 0xb2, 0xf, 0x26]], \
        [[0x1c6, 0xb3, 0xf, 0x11], [0x1c7, 0xb3, 0xf, 0x26]], \
        [[0x1c8, 0xb4, 0xf, 0x11], [0x1c9, 0xb4, 0xf, 0x26]], \
        [[0x1ca, 0xb5, 0xe, 0x15], [0x1cb, 0xb5, 0x16, 0xf]], \
        [[0x1cc, 0xb6, 0x1c, 0x1a]], \
        [[-1, 0xbd, 0x10, 0x18]] \
        ]

    # Avoid a problem with room A9.
    # You enter the doors in this room from the top. If they are connected to one of the rooms
    # which uses a "warp back" door, namely 48, 9b, AD, AE, AF, or BD, then upon returning to room A9,
    # you will be pushed outside the room and left unable to progress.
    # Avoid this by making sure room A9 isn't directly connected to a room with a "warp back" door.
    valid = False
    while not valid:
        RandomizeTowerSection(filebytes, first_room, remaining_rooms)
        valid = True
        check_addrs = [0x1b2, 0x1b3] # the two exits from room A9
        for check_addr in check_addrs:
            target_room = filebytes[0x92d0 + (check_addr * 3)]
            if target_room in [0x48, 0x9b, 0xad, 0xae, 0xaf, 0xbd]:
                valid = False
                break
        
    return
    
def AdjustMonsterGoldOffset(filebytes, gold_offset_adjust):
    for midx in range(0x00, 0xc8):
        byte_val = ReadCharacterGoldTableIndex(filebytes, midx)
        gold_offset = byte_val & 0x0f
        gold_offset += gold_offset_adjust
        gold_offset = max(1, gold_offset) # gold offset 0 is 0GP, which is just too cruel
        gold_offset = min(gold_offset, 0xf)
        byte_val = (byte_val & ~(0x0f))
        filebytes[0x0001aaee + (midx * 9)] = (byte_val | gold_offset)
    return
    
def AdjustGoldTableValues(filebytes, adjust_multiplier):
    for offset in range(0, 0x10):
        gold_val = ReadGoldTableValue(filebytes, offset)
        gold_val = int(gold_val * adjust_multiplier)
        WriteGoldTableValue(filebytes, offset, gold_val)
    return
    
def RandomizeSmallPics(filebytes, ffl2bytes):

    pc_male_addresses = [0x6000, 0x6200]
    npc_male_addresses = [0x7200, 0x7300, 0x7400]
    pc_female_addresses = [0x6100, 0x6300]
    npc_female_addresses = [0x6f00, 0x7100]
    
    if len(ffl2bytes) > 0:
        # copy FFL2 human and mutant pics
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6000], [0xc000])
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6100], [0xc100])
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6200], [0xc200])
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6300], [0xc300])
    
        # swap FFL NPC pics with human/mutant pics
        RandomlySwapSmallPics(filebytes, pc_male_addresses, npc_male_addresses)
        RandomlySwapSmallPics(filebytes, pc_female_addresses, npc_female_addresses)

        # copy FFL2 pics which resemble humans to human/mutant
        ffl2_male_addresses = [0xe900, 0xec00, 0xef00, 0xf300, 0xf600, 0xf900, 0xfc00, 0x10000, 0x10100]
        ffl2_female_addresses = [0xe500, 0xed00, 0xee00, 0xf200, 0xfd00]
        ffl_male_addresses = [] + pc_male_addresses + npc_male_addresses
        ffl_female_addresses = [] + pc_female_addresses + npc_female_addresses
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, ffl_male_addresses, ffl2_male_addresses)
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, ffl_female_addresses, ffl2_female_addresses)
        
        # copy monster pics
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6400], [0xe600, 0xe700, 0xe800]) # skel etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6500], [0xd800, 0xdd00, 0xe100, 0xe300]) # gob etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6600], [0xcc00, 0xd500, 0xd900, 0xe200]) # snek etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6700], [0xdb00, 0xdc00]) # bird etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6800], [0xda00, 0xdf00, 0xe400]) # fiend etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6900], [0xc600, 0xd300]) # octopus, plant, etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6a00], [0xcb00, 0xcd00, 0xea00]) # slime etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6b00], [0xd400, 0xd700, 0xd800]) # liz etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6c00], [0xce00, 0xcf00, 0xd000, 0xd200, 0xe000]) # insect etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6d00], [0xc800, 0xca00]) # man etc
        RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, [0x6e00], [0xd100]) # fish etc
    else:
        # swap FFL NPC pics with human/mutant pics
        RandomlySwapSmallPics(filebytes, pc_male_addresses, npc_male_addresses)
        RandomlySwapSmallPics(filebytes, pc_female_addresses, npc_female_addresses)

    return
    
def RandomlyCopyFFL2PicsToFFL(filebytes, ffl2bytes, ffl_addresses, ffl2_addresses):
    remaining_ffl2_addresses = list(ffl2_addresses)
    for ffl_addr in ffl_addresses:
        if random.randrange(3) == 0:
            continue
        ffl2_addr = random.choice(remaining_ffl2_addresses)
        for i in range(0, 0x100):
            filebytes[ffl_addr + i] = ffl2bytes[ffl2_addr + i]
        remaining_ffl2_addresses.remove(ffl2_addr)
    return
    
def RandomlySwapSmallPics(filebytes, pc_addresses, npc_addresses):
    npc_indices = list(range(0, len(npc_addresses)))
    for pc_addr in pc_addresses:
        if random.randrange(3) == 0:
            continue
        data_pc = filebytes[pc_addr:pc_addr+0x100]
        pick_idx = random.choice(npc_indices)
        npc_addr = npc_addresses[pick_idx]
        data_npc = filebytes[npc_addr:npc_addr+0x100]
        for i in range(0, 0x100):
            filebytes[pc_addr + i] = data_npc[i]
            filebytes[npc_addr + i] = data_pc[i]
        npc_indices.remove(pick_idx)
    return

MAP_X_MAX = 0x3e
MAP_Y_MAX = 0x3d

class MapChunkType(enum.Enum):
    TILE = 0 # Q in fledermaus
    SQUARE = 1 # E in fledermaus
    RING = 2 # A in fledermaus
    RING_HET = 3 # S in fledermaus
    CHECK = 4 # D in fledermaus
    CHECK_HET = 5 # F in fledermaus

class MapChunk:
    def Init(self, primary_tile, secondary_tile, pattern, x_pos, y_pos, x_size, y_size):
        self.primary_tile = primary_tile
        self.secondary_tile = secondary_tile
        self.pattern = pattern
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.x_size = x_size
        self.y_size = y_size
        
    def __init__(self):
        self.primary_tile = 0
        self.secondary_tile = 0
        self.pattern = MapChunkType.TILE
        self.x_pos = 0
        self.y_pos = 0
        self.x_size = 0
        self.y_size = 0
    
    def GetBytes(self):
        bytevals = []
        
        # [0]
        byte_val = self.primary_tile
        if self.pattern == MapChunkType.SQUARE:
            byte_val |= 0x80
        else:
            if self.pattern != MapChunkType.TILE:
                byte_val |= 0x40
        bytevals.append(byte_val)
        
        # [1]
        byte_val = self.y_pos << 2
        byte_val |= ((self.x_pos & 0xf0) >> 4)
        bytevals.append(byte_val)
        
        # [2]
        byte_val = (self.y_size >> 2)
        byte_val |= ((self.x_pos & 0x0f) << 4)
        bytevals.append(byte_val)
        
        # [3]
        if GetMapChunkSize(self.pattern) > 3:
            byte_val = self.x_size
            byte_val |= ((self.y_size % 4) * 0x40)
            bytevals.append(byte_val)
            
        # [4]
        if GetMapChunkSize(self.pattern) > 4:
            byte_val = self.secondary_tile
            if self.pattern == MapChunkType.RING_HET:
                byte_val |= 0x40
            if self.pattern == MapChunkType.CHECK:
                byte_val |= 0x80
            if self.pattern == MapChunkType.CHECK_HET:
                byte_val |= 0xc0
            bytevals.append(byte_val)
        return bytevals
    
    def MakeCopy(self):
        new_chunk = MapChunk()
        new_chunk.Init(self.primary_tile, self.secondary_tile, self.pattern, self.x_pos, self.y_pos, self.x_size, self.y_size)
        return new_chunk
    
def GetMapChunkSize(map_chunk_type):
    if map_chunk_type == MapChunkType.TILE:
        return 3
    if map_chunk_type == MapChunkType.SQUARE:
        return 4
    return 5
    
def RandomlyGenerateContinentMap(filebytes):
    
    walkable_tiles = [0x01, 0x02, 0x03, 0x16, 0x17, 0x19, 0x1b, 0x1c, 0x1d]
    backing_tile = 0x1e # mountain
    special_tiles = [0x0d, 0x12, 0x0e, 0x0f, 0x06, 0x08, 0x0a]
    
    best_map_chunks = []
    best_score = 0
    best_exits = []
    attempts = 0

    while attempts < 10:
        map_cols = [[backing_tile for y in range(0, MAP_Y_MAX + 1)] for x in range(0, MAP_X_MAX + 1)]
        chunks = []
        fits_in_size = False
        while not fits_in_size:
            attempts += 1
            chunks = []
            
            # define zones on the map where forest and desert are allowed
            # format: [[start_x, start_y], [end_x, end_y]]
            default_zone = [[0, 0], [MAP_X_MAX, MAP_Y_MAX]]
            forest_zone = []
            zone_size_x = random.randrange(int(0.5 * MAP_X_MAX), int(0.75 * MAP_X_MAX))
            zone_size_y = random.randrange(int(0.5 * MAP_Y_MAX), int(0.75 * MAP_Y_MAX))
            forest_zone.append([random.randrange(0, MAP_X_MAX - zone_size_x), random.randrange(0, MAP_Y_MAX - zone_size_y)])
            forest_zone.append([forest_zone[0][0] + zone_size_x, forest_zone[0][1] + zone_size_y])
            desert_zone = []
            zone_size_x = random.randrange(int(0.5 * MAP_X_MAX), int(0.75 * MAP_X_MAX))
            zone_size_y = random.randrange(int(0.5 * MAP_Y_MAX), int(0.75 * MAP_Y_MAX))
            desert_zone.append([random.randrange(0, MAP_X_MAX - zone_size_x), random.randrange(0, MAP_Y_MAX - zone_size_y)])
            desert_zone.append([desert_zone[0][0] + zone_size_x, desert_zone[0][1] + zone_size_y])
            
            # make some largeish areas
            tilechoices = [0x1b, 0x1c, 0x1d, 0x00]
            num_areas = 15
            for i in range(0, num_areas):
                if i < len(tilechoices):
                    tile = tilechoices[i]
                else:
                    tile = random.choice(tilechoices)
                if i > (num_areas - 2):
                    tile = 0x00
                new_chunk = MapChunk()
                new_chunk.Init(tile, tile, MapChunkType.CHECK, 0, 0, 0, 0)
                zone = default_zone
                if tile == 0x1c:
                    zone = forest_zone
                if tile == 0x1d:
                    zone = desert_zone
                new_chunk.x_pos = random.randrange(zone[0][0], min(zone[0][0] + 40, zone[1][0] - 1)) # don't start too close to the edge
                new_chunk.y_pos = random.randrange(zone[0][1], min(zone[0][1] + 40, zone[1][1] - 1)) # don't start too close to the edge
                new_chunk.x_size = random.randrange(min((zone[1][0] - new_chunk.x_pos) - 1, 16), (zone[1][0] - new_chunk.x_pos))
                new_chunk.y_size = random.randrange(min((zone[1][1] - new_chunk.y_pos) - 1, 16), (zone[1][1] - new_chunk.y_pos))
                chunks.append(new_chunk)
                SanityCheckChunks(chunks)
            
            # make rings and areas
            num_areas = 25
            for i in range(0, num_areas):
                tile = random.choice([0x1b, 0x1b, 0x1b, 0x1c, 0x1c, 0x1c, 0x1d, 0x1d, 0x1d, 0x17, 0x1e, 0x1e, 0x1e, 0x1e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                if i > (num_areas - 4):
                    tile = 0x00
                zone = default_zone
                if tile == 0x1c:
                    zone = forest_zone
                if tile in [0x17, 0x1d]: #spikes are also constrained to desert zone
                    zone = desert_zone
                new_chunk = MapChunk()
                new_chunk.Init(tile, tile, MapChunkType.RING, 0, 0, 0, 0)
                if random.randrange(4) == 0:
                    new_chunk.pattern = MapChunkType.CHECK
                new_chunk.x_pos = random.randrange(zone[0][0], zone[1][0] - 1)
                new_chunk.y_pos = random.randrange(zone[0][1], zone[1][1] - 1)
                new_chunk.x_size = random.randrange(1, (zone[1][0] - new_chunk.x_pos))
                new_chunk.y_size = random.randrange(1, (zone[1][1] - new_chunk.y_pos))
                chunks.append(new_chunk)
                SanityCheckChunks(chunks)
                
            # link all walkable patches
            EvaluateMap(map_cols, chunks, backing_tile)
            patches = GetWalkablePatches(map_cols, walkable_tiles)
            while len(patches) > 1:
                LinkTwoWalkablePatches(map_cols, chunks, patches)
                SanityCheckChunks(chunks)
                EvaluateMap(map_cols, chunks, backing_tile)
                patches = GetWalkablePatches(map_cols, walkable_tiles)

            # define data for entrances
            # Format of entrance data:
            # [0] chunks, [1] required area x, [2] required area y, [3] exit offsets, [4] exit position offset x, [5] exit position offset y
            # Chunk data:
            # [0] primary tile, [1] secondary tile, [2] chunk type, [3] x offset, [4] y offset, [5] chunk width, [6] chunk height
            entrances_data = []
            entrances_data.append([[[0x0c, 0x0c, MapChunkType.SQUARE, 0, 0, 1, 2]], 1, 2, [0x78], 0, 1]) # tower
            entrances_data.append([[[0x12, 0x12, MapChunkType.TILE, 0, 0, 1, 1]], 1, 1, [0x10e, 0x110], 0, 0]) # bandit cave
            entrances_data.append([[[0x0e, 0x0e, MapChunkType.TILE, 0, 0, 1, 1]], 1, 1, [0x100], 0, 0]) # town of hero
            entrances_data.append([[[0x0f, 0x0f, MapChunkType.TILE, 0, 0, 1, 1]], 1, 1, [0x10c], 0, 0]) # southeast town
            entrances_data.append([[[0x04, 0x04, MapChunkType.SQUARE, 0, 0, 2, 2]], 2, 2, [0x43, 0x101], 0, 1]) # castle shield
            entrances_data.append([[[0x04, 0x04, MapChunkType.SQUARE, 0, 0, 2, 1], [0x08, 0x08, MapChunkType.SQUARE, 0, 1, 2, 1]], 2, 2, [0x10b], 0, 1]) # castle armor
            entrances_data.append([[[0x04, 0x04, MapChunkType.SQUARE, 0, 0, 2, 1], [0x0a, 0x0a, MapChunkType.SQUARE, 0, 1, 2, 1]], 2, 2, [0x114], 0, 1]) # castle sword

            # place entrances
            num_chunks = len(chunks)
            entrances_attempts = 0
            best_map_valid = False
            best_entrances_score = 0
            best_entrances_chunks = []
            best_entrances_exits_data = []
            while entrances_attempts < 50:
                # print("entrances attempt", entrances_attempts)
                map_valid = False
                del(chunks[num_chunks:])
                EvaluateMap(map_cols, chunks, backing_tile)
                entrances_attempts += 1
                need_abort = False
                for entrance in entrances_data:
                    new_chunks = []
                    for chunk_data in entrance[0]:
                        new_chunk = MapChunk()
                        new_chunk.Init(chunk_data[0], chunk_data[1], chunk_data[2], chunk_data[3], chunk_data[4], chunk_data[5], chunk_data[6])
                        new_chunks.append(new_chunk)
                    placed = TryPlaceSpecialTile(filebytes, map_cols, chunks, walkable_tiles, entrance[1], entrance[2], new_chunks, entrance[3], entrance[4], entrance[5])
                    SanityCheckChunks(chunks)
                    if not placed:
                        need_abort = True
                        break
                    EvaluateMap(map_cols, chunks, backing_tile)
                    if need_abort:
                        break
                if need_abort:
                    continue
                    
                # if a walkable area was blocked off by placing towns etc, try again
                patches = GetWalkablePatches(map_cols, walkable_tiles)
                if len(patches) > 1:
                    continue
                    
                this_score = CalculateContinentMapScore(map_cols, special_tiles)
                if this_score > best_entrances_score:
                    # print("new best score:", this_score)
                    best_entrances_score = this_score
                    best_entrances_chunks = chunks[num_chunks:]
                    best_map_valid = True
                    best_entrances_exits_data = filebytes[0x92d0:0x985e]
                
            if not best_map_valid:
                continue
                
            del(chunks[num_chunks:])
            for c in best_entrances_chunks:
                chunks.append(c)
            EvaluateMap(map_cols, chunks, backing_tile)
            for i in range(0, len(best_entrances_exits_data)):
                filebytes[0x92d0 + i] = best_entrances_exits_data[i]

            # add up to 10 bridges
            for i in range(0, 10):
                total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
                if total_size >= 325:
                    break
                if TryAddRandomBridge(map_cols, chunks, 0x00, walkable_tiles, 0x02, 0x03):
                    SanityCheckChunks(chunks)
                    EvaluateMap(map_cols, chunks, backing_tile)

            total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
            fits_in_size = (total_size <= 328)
            
        # give the new map a score based on distances between entrances - higher is better
        # print("map created")
        this_score = CalculateContinentMapScore(map_cols, special_tiles)
        if this_score > best_score:
            # print("new best score:", this_score)
            best_score = this_score
            best_map_chunks = chunks
            # store a copy of exits data, as it's overwritten during map generation
            best_exits_data = filebytes[0x92d0:0x985e]
        else:
            # print("doesn't beat best score:", this_score)
            pass

    WriteMapChunks(filebytes, best_map_chunks, 0xc000)
    for i in range(0, len(best_exits_data)):
        filebytes[0x92d0 + i] = best_exits_data[i]
    
    return
    
def SanityCheckChunks(chunks):
    for c in chunks:
        if (c.x_pos < 0) or (c.x_pos > MAP_X_MAX):
            raise Exception("Chunk with bad x position: " + str(hex(c.x_pos)))
        if (c.y_pos < 0) or (c.y_pos > MAP_X_MAX):
            raise Exception("Chunk with bad y position: " + str(hex(c.y_pos)))
        if ((c.x_pos + c.x_size) > MAP_X_MAX):
            raise Exception("Chunk with bad x size: pos " + str(hex(c.x_pos)) + " size " + str(hex(c.x_size)))
        if ((c.y_pos + c.y_size) > MAP_Y_MAX):
            raise Exception("Chunk with bad y size: pos " + str(hex(c.y_pos)) + " size " + str(hex(c.y_size)))
    return
            
    
def CalculateContinentMapScore(map_cols, special_tiles):
    this_score = 0
    for special_tile in special_tiles:
        locations = [[x, y] for x in range(0, MAP_X_MAX + 1) for y in range(0, MAP_Y_MAX + 1) if map_cols[x][y] == special_tile]
        if len(locations) != 1:
            raise Exception("Special tile " + str(hex(special_tile)) + " appears " + str(len(locations)) + " times")
        this_loc = locations[0]
        other_locations = [[x, y] for x in range(0, MAP_X_MAX + 1) for y in range(0, MAP_Y_MAX + 1) if ((map_cols[x][y] in special_tiles) and map_cols[x][y] != special_tile)]
        closest_distance = min([ math.sqrt((abs(loc[0] - this_loc[0]) * abs(loc[0] - this_loc[0])) + (abs(loc[1] - this_loc[1]) * abs(loc[1] - this_loc[1]))) \
            for loc in other_locations])
        this_score += closest_distance
    return this_score

def TryPlaceSpecialTile(filebytes, map_cols, chunks, walkable_tiles, required_area_x, required_area_y, new_chunks, exit_indices, exit_offset_x, exit_offset_y):
    start_pos = FindWalkablePatch(map_cols, walkable_tiles, required_area_x, required_area_y)
    if len(start_pos) < 2:
        return False
    for new_chunk in new_chunks:
        new_chunk.x_pos += start_pos[0]
        new_chunk.y_pos += start_pos[1]
        chunks.append(new_chunk)
    for exit_idx in exit_indices:
        SetExitPosition(filebytes, exit_idx, start_pos[0] + exit_offset_x, start_pos[1] + exit_offset_y)
    return True
    
def SetExitPosition(filebytes, exit_offset, x, y):
    filebytes[0x92d0 + (exit_offset * 3) + 1] = x
    filebytes[0x92d0 + (exit_offset * 3) + 2] = y
    return
    
def GetExitPosition(filebytes, exit_offset):
    return [filebytes[0x92d0 + (exit_offset * 3) + 1], filebytes[0x92d0 + (exit_offset * 3) + 2]]
    
def EvaluateMap(map_cols, chunks, default_tile):
    for x in range(0, MAP_X_MAX + 1):
        for y in range(0, MAP_Y_MAX + 1):
            map_cols[x][y] = default_tile
    
    for chunk in chunks:
        if chunk.pattern == MapChunkType.TILE:
            map_cols[chunk.x_pos][chunk.y_pos] = chunk.primary_tile
        if chunk.pattern == MapChunkType.SQUARE:
            tile = chunk.primary_tile
            for y in range(chunk.y_pos, chunk.y_pos + chunk.y_size):
                for x in range(chunk.x_pos, chunk.x_pos + chunk.x_size):
                    map_cols[x][y] = tile
                    tile += 1
                    tile %= 0x20
        if chunk.pattern == MapChunkType.RING:
            tile_offset = 1
            tiles = [chunk.secondary_tile, chunk.primary_tile]
            for y in range(chunk.y_pos, chunk.y_pos + chunk.y_size):
                for x in range(chunk.x_pos, chunk.x_pos + chunk.x_size):
                    if (x == chunk.x_pos) or (y == chunk.y_pos) or (x == (chunk.x_pos + chunk.x_size - 1)) or (y == (chunk.y_pos + chunk.y_size - 1)):
                        map_cols[x][y] = tiles[tile_offset]
                    tile_offset += 1
                    tile_offset %= 2
        if chunk.pattern == MapChunkType.RING_HET:
            tile_offset = 1
            tiles = [chunk.secondary_tile, chunk.primary_tile]
            for y in range(chunk.y_pos, chunk.y_pos + chunk.y_size):
                for x in range(chunk.x_pos, chunk.x_pos + chunk.x_size):
                    if (x == chunk.x_pos) or (y == chunk.y_pos) or (x == (chunk.x_pos + chunk.x_size - 1)) or (y == (chunk.y_pos + chunk.y_size - 1)):
                        map_cols[x][y] = tiles[tile_offset]
                    tile_offset += 1
                    tile_offset %= 2
            map_cols[chunk.x_pos][chunk.y_pos] = chunk.secondary_tile # top left
            map_cols[chunk.x_pos + chunk.x_size - 1][chunk.y_pos] = ((chunk.secondary_tile + 1) % 0x20) # top right
            map_cols[chunk.x_pos][chunk.y_pos + chunk.y_size - 1] = ((chunk.secondary_tile + 2) % 0x20) # bottom left
            map_cols[chunk.x_pos + chunk.x_size - 1][chunk.y_pos + chunk.y_size - 1] = ((chunk.secondary_tile + 3) % 0x20) # bottom right
        if chunk.pattern == MapChunkType.CHECK:
            # print("chunk tile", hex(chunk.secondary_tile), "x", hex(chunk.x_pos), "y", hex(chunk.y_pos), "size x", hex(chunk.x_size), "y", hex(chunk.y_size))
            tile_offset = 0
            tiles = [chunk.secondary_tile, chunk.primary_tile]
            for y in range(chunk.y_pos, chunk.y_pos + chunk.y_size):
                for x in range(chunk.x_pos, chunk.x_pos + chunk.x_size):
                    map_cols[x][y] = tiles[tile_offset]
                    tile_offset += 1
                    tile_offset %= 2
        if chunk.pattern == MapChunkType.CHECK_HET:
            tile_offset = 0
            tiles = [chunk.secondary_tile, chunk.primary_tile]
            for y in range(chunk.y_pos, chunk.y_pos + chunk.y_size):
                for x in range(chunk.x_pos, chunk.x_pos + chunk.x_size):
                    map_cols[x][y] = tiles[tile_offset]
                    tile_offset += 1
                    tile_offset %= 2
            map_cols[chunk.x_pos][chunk.y_pos] = chunk.secondary_tile # top left
            map_cols[chunk.x_pos + chunk.x_size - 1][chunk.y_pos] = ((chunk.secondary_tile + 1) % 0x20) # top right
            map_cols[chunk.x_pos][chunk.y_pos + chunk.y_size - 1] = ((chunk.secondary_tile + 2) % 0x20) # bottom left
            map_cols[chunk.x_pos + chunk.x_size - 1][chunk.y_pos + chunk.y_size - 1] = ((chunk.secondary_tile + 3) % 0x20) # bottom right
    return

def GetWalkablePatches(map_cols, walkable_tiles):
    patches = []
    for x in range(0, MAP_X_MAX):
        for y in range(0, MAP_Y_MAX):
            cell_ref = [x, y]
            if map_cols[x][y] in walkable_tiles:
                if not any([cell_ref in patch for patch in patches]):
                    patches.append(GetWalkablePatchByFloodFill(map_cols, cell_ref, walkable_tiles))
    return patches
    
def GetWalkablePatchByFloodFill(map_cols, initial_cell, walkable_tiles):
    patch = []
    cells_to_evaluate = []
    if map_cols[initial_cell[0]][initial_cell[1]] in walkable_tiles:
        cells_to_evaluate.append(initial_cell)
    while len(cells_to_evaluate) > 0:
        cell = list(cells_to_evaluate[0])
        patch.append(cell)
        del(cells_to_evaluate[0])
        # Test the four cells adjacent to this cell
        if cell[0] > 0:
            test_cell = [cell[0] - 1, cell[1]]
            if (not test_cell in patch) and (not test_cell in cells_to_evaluate):
                if map_cols[test_cell[0]][test_cell[1]] in walkable_tiles:
                    cells_to_evaluate.append(test_cell)
        if cell[0] < MAP_X_MAX:
            test_cell = [cell[0] + 1, cell[1]]
            if (not test_cell in patch) and (not test_cell in cells_to_evaluate):
                if map_cols[test_cell[0]][test_cell[1]] in walkable_tiles:
                    cells_to_evaluate.append(test_cell)
        if cell[1] > 0:
            test_cell = [cell[0], cell[1] - 1]
            if (not test_cell in patch) and (not test_cell in cells_to_evaluate):
                if map_cols[test_cell[0]][test_cell[1]] in walkable_tiles:
                    cells_to_evaluate.append(test_cell)
        if cell[1] < MAP_Y_MAX:
            test_cell = [cell[0], cell[1] + 1]
            if (not test_cell in patch) and (not test_cell in cells_to_evaluate):
                if map_cols[test_cell[0]][test_cell[1]] in walkable_tiles:
                    cells_to_evaluate.append(test_cell)            
    return patch
    
def LinkTwoWalkablePatches(map_cols, chunks, patches):
    # find closest cells
    closest_pair = []
    closest_pair_distance = 0x40 * 0x40
    for cell_a in patches[0]:
        for cell_b in patches[1]:
            x_dist = abs(cell_a[0] - cell_b[0])
            y_dist = abs(cell_a[1] - cell_b[1])
            dist = math.sqrt((x_dist * x_dist) + (y_dist * y_dist))
            if dist < closest_pair_distance:
                closest_pair = [cell_a, cell_b]
                closest_pair_distance = dist
    
    # link closest cells with a ring
    min_x = min(closest_pair[0][0], closest_pair[1][0])
    max_x = max(closest_pair[0][0], closest_pair[1][0])
    min_y = min(closest_pair[0][1], closest_pair[1][1])
    max_y = max(closest_pair[0][1], closest_pair[1][1])
    new_chunk = MapChunk()
    tile_choices = [map_cols[closest_pair[0][0]][closest_pair[0][1]], map_cols[closest_pair[1][0]][closest_pair[1][1]]]
    new_chunk.primary_tile = random.choice(tile_choices)
    new_chunk.secondary_tile = new_chunk.primary_tile
    new_chunk.pattern = MapChunkType.RING
    new_chunk.x_pos = min_x
    new_chunk.y_pos = min_y
    new_chunk.x_size = (max_x - min_x) + 1
    new_chunk.y_size = (max_y - min_y) + 1
    chunks.append(new_chunk)
    return
    
def FindWalkablePatch(map_cols, walkable_tiles, x_size, y_size):
    random_offset_x = random.randrange(0, MAP_X_MAX + 1)
    random_offset_y = random.randrange(0, MAP_Y_MAX + 1)
    for x_idx in range(0, MAP_X_MAX + 1):
        for y_idx in range(0, MAP_Y_MAX + 1):
            start_x = (x_idx + random_offset_x) % (MAP_X_MAX + 1)
            start_y = (y_idx + random_offset_y) % (MAP_Y_MAX + 1)
            is_walkable = True
            for x in range(start_x, start_x + x_size):
                for y in range(start_y, start_y + y_size):
                    if not map_cols[x][y] in walkable_tiles:
                        is_walkable = False
                        break
                if not is_walkable:
                    break
            if is_walkable:
                return [start_x, start_y]
    return []
    
def FindFirstWalkableAreaInCellList(map_cols, cell_list, walkable_tiles, x_size, y_size):
    for cell_idx in range(0, len(cell_list)):
        x = cell_list[cell_idx][0]
        y = cell_list[cell_idx][1]
        valid_area = True
        for x_offset in range(0, x_size):
            for y_offset in range(0, y_size):
                if not [x + x_offset, y + y_offset] in cell_list:
                    valid_area = False
                    break
                if not map_cols[x + x_offset][y + y_offset] in walkable_tiles:
                    valid_area = False
                    break
            if not valid_area:
                break
        if valid_area:
            return cell_list[cell_idx]
    return []
    
def TryAddRandomBridge(map_cols, chunks, water_tile, walkable_tiles, horiz_bridge_tile, vert_bridge_tile):
    offset_x = random.randrange(0, MAP_X_MAX)
    offset_y = random.randrange(0, MAP_Y_MAX)
    for i in range(0, MAP_X_MAX + 1):
        x = (i + offset_x) % (MAP_X_MAX + 1)
        if (x == 0) or (x == MAP_X_MAX):
            continue
        for j in range(0, MAP_Y_MAX + 1):
            y = (j + offset_y) % (MAP_Y_MAX + 1)
            if (y == 0) or (y == MAP_Y_MAX):
                continue
            tile = map_cols[x][y]
            if (tile != horiz_bridge_tile) and (tile != vert_bridge_tile) and (tile in walkable_tiles):
                top_tile = map_cols[x][y - 1]
                top_l_tile = map_cols[x - 1][y - 1]
                top_r_tile = map_cols[x + 1][y - 1]
                bottom_tile = map_cols[x][y + 1]
                bottom_l_tile = map_cols[x - 1][y + 1]
                bottom_r_tile = map_cols[x + 1][y + 1]
                left_tile = map_cols[x - 1][y]
                right_tile = map_cols[x + 1][y]
                if (top_l_tile == water_tile) or (top_r_tile == water_tile) or (bottom_l_tile == water_tile) or (bottom_r_tile == water_tile):
                    continue
                if (top_tile == water_tile) and (bottom_tile == water_tile) and (left_tile in walkable_tiles) and (right_tile in walkable_tiles):
                    new_chunk = MapChunk()
                    new_chunk.Init(horiz_bridge_tile, horiz_bridge_tile, MapChunkType.TILE, x, y, 1, 1)
                    chunks.append(new_chunk)
                    return True
                if (left_tile == water_tile) and (right_tile == water_tile) and (top_tile in walkable_tiles) and (bottom_tile in walkable_tiles):
                    new_chunk = MapChunk()
                    new_chunk.Init(vert_bridge_tile, vert_bridge_tile, MapChunkType.TILE, x, y, 1, 1)
                    chunks.append(new_chunk)
                    return True
    return False
    
def WriteMapChunks(filebytes, chunks, start_addr):
    addr = start_addr
    for chunk in chunks:
        chunk_bytes = chunk.GetBytes()
        for b in chunk_bytes:
            filebytes[addr] = b
            addr += 1
    filebytes[addr] = 0xff
    return
    
class MultiRoomDungeonParams:
    def __init__(self):
        self.walkable_tiles = []
        self.map_fill_tile = 0x00
        self.backing_tile = 0x00
        self.room_open_tile = 0x00
        self.chunk_tile_choices = []
        self.rooms_max_size_bytes = -1
        self.map_start_address = -1
        self.num_rooms = -1
        self.min_room_size = -1
        self.min_distance_between_rooms = -1
        self.min_room_y = -1
        self.max_size_bytes = -1
        self.get_valid_func = None
        # List of RoomPlacements. They will be processed in order of size, largest first
        self.room_placements = []
        self.chunks_must_change_walkable = False
        self.make_chunk_func = None
        self.non_walkable_area_placements = []
        self.non_walkable_area_placements_room_id = 0
        
def RandomlyGenerateMultiRoomDungeonMap(params, filebytes):
    verbose = False

    map_success = False
    while not map_success:
        if verbose:
            print("    map pass...")
        map_success = True
        map_cols = [[params.backing_tile for y in range(0, MAP_Y_MAX + 1)] for x in range(0, MAP_X_MAX + 1)]
        chunks = []
        prev_map_cols = []
        if params.chunks_must_change_walkable:
            prev_map_cols = [[params.backing_tile for y in range(0, MAP_Y_MAX + 1)] for x in range(0, MAP_X_MAX + 1)]
        
        # map fill tile backing
        new_chunk = MapChunk()
        new_chunk.Init(params.map_fill_tile, params.map_fill_tile, MapChunkType.CHECK, 0, 0, MAP_X_MAX, MAP_Y_MAX)
        chunks.append(new_chunk)
        SanityCheckChunks(chunks)
        
        # place initial room rectangles
        num_prev_chunks = len(chunks)
        patches = []
        valid = False
        while not valid:
            valid = True
            patches = []
            chunks = chunks[:num_prev_chunks]
            for room_idx in range(0, params.num_rooms):
                tile = params.room_open_tile
                new_chunk = MapChunk()
                new_chunk.Init(tile, tile, MapChunkType.CHECK, 0, 0, params.min_room_size, params.min_room_size)
                new_chunk.x_pos = random.randrange(0, MAP_X_MAX - params.min_room_size)
                new_chunk.y_pos = random.randrange(params.min_room_y, MAP_Y_MAX - params.min_room_size)
                chunks.append(new_chunk)
                SanityCheckChunks(chunks)
                EvaluateMap(map_cols, chunks, params.backing_tile)
                patches = GetWalkablePatches(map_cols, params.walkable_tiles)
                if len(patches) != (room_idx + 1):
                    valid = False
                    break
            if valid:
                valid = params.get_valid_func(patches)
            
        if verbose:
            print("  placed initial rectangles")
        
        num_prev_chunks = len(chunks)
        
        successful_changes = 0
        
        total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
        while total_size < (params.rooms_max_size_bytes - 6):
            num_prev_chunks = len(chunks)
            if params.chunks_must_change_walkable:
                EvaluateMap(prev_map_cols, chunks, params.backing_tile)
            
            # add a chunk
            if params.make_chunk_func != None:
                new_chunk = params.make_chunk_func()
                chunks.append(new_chunk)
            else:
                tile = random.choice(params.chunk_tile_choices)
                new_chunk = MapChunk()
                chunk_type = MapChunkType.CHECK
                if random.randrange(2) == 0:
                    chunk_type = MapChunkType.RING
                new_chunk.Init(tile, tile, chunk_type, 0, 0, 0, 0)
                new_chunk.x_pos = random.randrange(0, MAP_X_MAX - 1)
                new_chunk.y_pos = random.randrange(0, MAP_Y_MAX - 1)
                new_chunk.x_size = random.randrange(1, min(int(0.5 * MAP_X_MAX), MAP_X_MAX - new_chunk.x_pos))
                new_chunk.y_size = random.randrange(1, min(int(0.5 * MAP_Y_MAX), MAP_Y_MAX - new_chunk.y_pos))
                chunks.append(new_chunk)
            SanityCheckChunks(chunks)

            EvaluateMap(map_cols, chunks, params.backing_tile)
            patches = GetWalkablePatches(map_cols, params.walkable_tiles)
                
            # check criteria
            valid = params.get_valid_func(patches)
            if valid and params.chunks_must_change_walkable:
                valid = not GetMapsWalkabilitySame(map_cols, prev_map_cols, params.walkable_tiles, new_chunk.x_pos, new_chunk.y_pos, new_chunk.x_size, new_chunk.y_size)
            if valid:
                RemoveIneffectiveChunks(chunks, params.backing_tile)
            else:
                chunks = chunks[:num_prev_chunks]
            
            total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
            
        if verbose:
            print("  created map structure")

        # sort walkable patches by size
        patch_indices = list(range(0, len(patches)))
        patch_indices.sort(key=lambda patch_idx: len(patches[patch_idx]), reverse=True)
        
        # place elements
        num_prev_chunks = len(chunks)
        placement_success = False
        placement_attempts = 0
        
        while (not placement_success) and (placement_attempts < 50):
            if verbose:
                print("  placement attempt", placement_attempts)
            placement_success = True
            placement_attempts += 1
            chunks = chunks[:num_prev_chunks]
            for rp in range(0, len(params.room_placements)):
                params.room_placements[rp].remaining_cells = list(patches[patch_indices[rp]])
            
            num_patches = len(patches)

            for room in params.room_placements:
                # print("    room with", len(room.room_entrance_placements), "placements", room.remaining_cells)
                placed_items = []
                for room_entrance_placement in room.room_entrance_placements:
                    # print("      placement with non_walkable_tiles", room_entrance_placement.non_walkable_tiles)
                    valid_cells = []
                    for cell_idx in range(0, len(room.remaining_cells)):
                        cell = room.remaining_cells[cell_idx]
                        valid = True
                        if valid:
                            for chunk in room_entrance_placement.chunks:
                                x = chunk.x_pos + cell[0]
                                y = chunk.y_pos + cell[1]
                                if (x < 0) or (x > MAP_X_MAX) or (y < 0) or (y > MAP_Y_MAX):
                                    # print("              invalid x", hex(x), "or y", hex(y), "chunk.x_pos", chunk.x_pos, "chunk.y_pos", chunk.y_pos, "cell[0]", cell[0], "cell[1]", cell[1])
                                    valid = False
                                    break
                                if (x + chunk.x_size > MAP_X_MAX) or (y + chunk.y_size > MAP_Y_MAX):
                                    # print("              invalid size")
                                    valid = False
                                    break
                        for tile_offset in room_entrance_placement.non_walkable_tiles:
                            x = cell[0] + tile_offset[0]
                            y = cell[1] + tile_offset[1]
                            if (x <= MAP_X_MAX) and (y <= MAP_Y_MAX):
                                if map_cols[x][y] in params.walkable_tiles:
                                    # print("              invalid non_walkable_tiles")
                                    valid = False
                                    break
                        if valid:
                            valid_cells.append(cell)
                            
                    if len(valid_cells) == 0:
                        # print("       failed to place entrance!")
                        placement_success = False
                        break

                    # print("       placed entrance ")
                        
                    # sort valid cells by distance from items placed already
                    valid_cells.sort(key=lambda cell:(sum([GetDistanceBetweenCells(cell, placed_cell) for placed_cell in placed_items])), reverse=True)
                    if len(valid_cells) > 2:
                        # discard half of the valid cells which are closest to items placed already
                        valid_cells = valid_cells[:int(len(valid_cells) / 2)]
                    # choose from one of the remaining valid cells
                    cell = random.choice(valid_cells)

                    if room_entrance_placement.write_exit:
                        if verbose:
                            print("        place entrance at cell", str(hex(cell[0])), str(hex(cell[1])))
                        one_way_exit = [room_entrance_placement.exit_addr, room.room_id, cell[0] + room_entrance_placement.exit_offset[0], cell[1] + room_entrance_placement.exit_offset[1]]
                        WriteOneWayExits(filebytes, [one_way_exit])
                    for npc_addr in room_entrance_placement.exit_npc_pos_start_addr:
                        filebytes[npc_addr] = cell[0] + room_entrance_placement.exit_npc_pos_offset[0]
                        filebytes[npc_addr + 1] = cell[1] + room_entrance_placement.exit_npc_pos_offset[1]
                    room.remaining_cells.remove(cell)
                    for orig_chunk in room_entrance_placement.chunks:
                        new_chunk = orig_chunk.MakeCopy()
                        new_chunk.x_pos += cell[0]
                        new_chunk.y_pos += cell[1]
                        chunks.append(new_chunk)
                    SanityCheckChunks(chunks)
                    placed_items.append(cell)
                    EvaluateMap(map_cols, chunks, params.backing_tile)
                    
                if not placement_success:
                    break
                        
                for npc_placement in room.room_npc_placements:
                    valid_cells = []
                    for cell_idx in range(0, len(room.remaining_cells)):
                        cell = room.remaining_cells[cell_idx]
                        if all([[cell[0] + required_cell[0], cell[1] + required_cell[1]] in room.remaining_cells for required_cell in npc_placement.required_cells]):
                            valid_cells.append(cell)
                            
                    if len(valid_cells) == 0:
                        # print("       failed to place npc!")
                        placement_success = False
                        break
                        
                    # sort valid cells by distance from items placed already
                    valid_cells.sort(key=lambda cell:(sum([GetDistanceBetweenCells(cell, placed_cell) for placed_cell in placed_items])), reverse=True)
                    if len(valid_cells) > 2:
                        # discard half of the valid cells which are closest to items placed already
                        valid_cells = valid_cells[:int(len(valid_cells) / 2)]
                    # choose from one of the remaining valid cells
                    cell = random.choice(valid_cells)

                    filebytes[npc_placement.pos_start_addr] = cell[0]
                    filebytes[npc_placement.pos_start_addr+1] = cell[1]
                    for required_cell in npc_placement.required_cells:
                        room.remaining_cells.remove([cell[0] + required_cell[0], cell[1] + required_cell[1]])
                    placed_items.append(cell)
                    
                if not placement_success:
                    break
                    
            if placement_success:
                EvaluateMap(map_cols, chunks, params.backing_tile)
                for placement in params.non_walkable_area_placements:
                    valid_cells = []
                    for x in range(0, MAP_X_MAX + 1):
                        for y in range(0, MAP_Y_MAX + 1):
                            valid = True
                            for tile_offset in placement.non_walkable_tiles:
                                tile_x = x + tile_offset[0]
                                tile_y = x + tile_offset[1]
                                if (tile_x >= 0) and (tile_x <= MAP_X_MAX) and (tile_y >= 0) and (tile_y <= MAP_Y_MAX):
                                    if map_cols[tile_x][tile_y] in params.walkable_tiles:
                                        valid = False
                                        break
                            if valid:
                                for chunk in placement.chunks:
                                    tile_x = chunk.x_pos + x
                                    tile_y = chunk.y_pos + y
                                    if (tile_x < 0) or (tile_x > MAP_X_MAX) or (tile_y < 0) or (tile_y > MAP_Y_MAX):
                                        # print("              invalid x", hex(x), "or y", hex(y), "chunk.x_pos", chunk.x_pos, "chunk.y_pos", chunk.y_pos, "cell[0]", cell[0], "cell[1]", cell[1])
                                        valid = False
                                        break
                                    if (tile_x + chunk.x_size > MAP_X_MAX) or (tile_y + chunk.y_size > MAP_Y_MAX):
                                        # print("              invalid size")
                                        valid = False
                                        break
                            if valid:
                                valid_cells.append([x, y])
                    
                    if len(valid_cells) == 0:
                        # print("    failed to place non_walkable_area_placement!")
                        placement_success = False
                        break
                        
                    if len(valid_cells) > 0:
                        cell = random.choice(valid_cells)
                        for orig_chunk in placement.chunks:
                            new_chunk = orig_chunk.MakeCopy()
                            new_chunk.x_pos += cell[0]
                            new_chunk.y_pos += cell[1]
                            chunks.append(new_chunk)
                        SanityCheckChunks(chunks)
                        EvaluateMap(map_cols, chunks, params.backing_tile)
                        
                        if placement.write_exit:
                            room_id = params.non_walkable_area_placements_room_id
                            one_way_exit = [placement.exit_addr, room_id, cell[0] + placement.exit_offset[0], cell[1] + placement.exit_offset[1]]
                            WriteOneWayExits(filebytes, [one_way_exit])

                        
            # sanity check total size
            total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
            if total_size > params.max_size_bytes:
                # print("       map too big!", total_size)
                placement_success = False
                
            # check get_valid_func again
            patches = GetWalkablePatches(map_cols, params.walkable_tiles)
            if not params.get_valid_func(patches):
                # print("       get_valid_func failed!")
                placement_success = False
             
        if verbose:
            print("  placement_success:", placement_success)

        if not placement_success:
            map_success = False
            
        if map_success:
            # sanity check total size
            total_size = 1 + sum([GetMapChunkSize(c.pattern) for c in chunks])
            if total_size > params.max_size_bytes:
                if verbose:
                    print("       map too big!", total_size)
                map_success = False

        if map_success:
            # check get_valid_func again
            patches = GetWalkablePatches(map_cols, params.walkable_tiles)
            if not params.get_valid_func(patches):
                if verbose:
                    print("       get_valid_func failed!")
                map_success = False

        # WriteMapChunks(filebytes, chunks, params.map_start_address)
        # WriteBytesToFile(filebytes, r"D:\_downloads\_emu\hacking\hacked_roms\TEMP_FFL.gb")
            
    WriteMapChunks(filebytes, chunks, params.map_start_address)
    
    return
    
def GetMapsWalkabilitySame(map_cols_a, map_cols_b, walkable_tiles, x_start, y_start, x_size, y_size):
    for x in range(x_start, (x_start + x_size + 1)):
        for y in range(y_start, (y_start + y_size + 1)):
            if (map_cols_a[x][y] in walkable_tiles) != (map_cols_b[x][y] in walkable_tiles):
                return False
    return True
    
def RandomlyGenerateBanditCaveMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x02, 0x03, 0x04, 0x05, 0x16, 0x18, 0x19, 0x1a, 0x1b, 0x1d]
    params.map_fill_tile = 0x00
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x1d # green (open)
    params.chunk_tile_choices = ([0x1d] * 5) + [0x18] + ([0x00] * 5) # either green (open), light rock (open), or light rock (block)
    params.rooms_max_size_bytes = 140
    params.map_start_address = 0xcfa0
    params.num_rooms = 5
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 190
    
    def GetBanditCaveValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 20 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        for patch in patches:
            if ApproxCountNonOverlappingRegionsInPatch(patch, 2, 2) < 3:
                return False
        return True
        
    params.get_valid_func = GetBanditCaveValid
    
    # define data
    
    room_placements = []
    
    # define the three one-way rooms
    empty_room_placement = RoomEntrancePlacement()
    empty_room_placement.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2]]
    empty_room_placement.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x12, 0x12, MapChunkType.SQUARE, 0, -2, 1, 2)
    empty_room_placement.chunks.append(new_chunk)
    treasure_room_placement = MakeDoorEntrancePlacement(0x0f, 0x12)
    bandit_chief_room_placement = MakeDoorEntrancePlacement(0x11, 0x12)

    # one of the rooms will be locked - decide which
    # (can't be chief's room, as defeating the chief unlocks the locked room)
    cave_2_locked_room = treasure_room_placement
    remaining_rooms = [empty_room_placement, bandit_chief_room_placement]
    if random.randrange(0, 2) == 0:
        cave_2_locked_room = empty_room_placement
        remaining_rooms = [treasure_room_placement, bandit_chief_room_placement]
    
    ######################################################################################
    # bandit cave 1
    rp = RoomPlacement()
    rp.room_id = 0x5e
    
    # exit from bandit cave 1 back to the surface
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x07, 0x1e, 0x0ff))
    
    # exits from bandit cave 1 to remaining rooms
    for i in range(len(remaining_rooms) - 1, -1, -1):
        if random.randrange(0, 2) == 0:
            rp.room_entrance_placements.append(remaining_rooms[i])
            del(remaining_rooms[i])
    
    # exit from bandit cave 1 to bandit cave 2
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, 1], [-1, 1], [1, 1], [0, 2], [-1, 2], [1, 2]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x0a, 0x0a, MapChunkType.TILE, 0, 1, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = 0x112
    rep.exit_offset = [0, 0]
    rp.room_entrance_placements.append(rep)
    
    # npc 0
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa894
    rp.room_npc_placements.append(rnp)
    
    # npc 1
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa89b
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    ######################################################################################
    # bandit cave 2
    rp = RoomPlacement()
    rp.room_id = 0x5f
    
    # exit from bandit cave 2 back to bandit cave 1
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x09, 0x1e, 0x10f))
    
    # exit from bandit cave 1 to remaining rooms
    for room in remaining_rooms:
        rp.room_entrance_placements.append(room)
    
    # exit from bandit cave 2 to locked room (either empty room or treasure room)
    rep = cave_2_locked_room
    rep.exit_npc_pos_offset = [0, -1]
    rep.exit_npc_pos_start_addr.append(0xa8ab) # "won't open" message
    rp.room_entrance_placements.append(rep)
    
    # npc 0
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa8a4
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)
    
    ######################################################################################
    # bandit treasure room
    rp = RoomPlacement()
    rp.room_id = 0x61
    
    # warp back door from bandit treasure room
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x12, 0x111))
    
    # npc 0 (chest)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
    rnp.pos_start_addr = 0xa8bd
    rp.room_npc_placements.append(rnp)
    
    # npc 1 (chest)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
    rnp.pos_start_addr = 0xa8c4
    rp.room_npc_placements.append(rnp)

    # npc 2 (chest)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
    rnp.pos_start_addr = 0xa8cb
    rp.room_npc_placements.append(rnp)

    room_placements.append(rp)

    ######################################################################################
    # bandit chief's room
    rp = RoomPlacement()
    rp.room_id = 0x60
    
    # warp back door from bandit chief's room
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x12, 0x113))
    
    # npc 0
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
    rnp.pos_start_addr = 0xa8b4
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)
    
    ######################################################################################
    # bandit empty room
    rp = RoomPlacement()
    rp.room_id = 0x62
    
    room_placements.append(rp)
    
    # warp back door from bandit treasure room
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x12, 0x10d))
    
    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return
    
def RandomlyGenerateCastleSwordMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x03, 0x04, 0x07, 0x0b, 0x0e, 0x0f]
    params.map_fill_tile = 0x01
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x03 # grass (open)
    # tile choices: grass (open), light rock (open), light rock (block)
    params.chunk_tile_choices = ([0x03] * 5)  + ([0x01] * 5) + [0x04]
    params.rooms_max_size_bytes = 190
    params.map_start_address = 0xccd9
    params.num_rooms = 4
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 226
    
    def GetCastleSwordValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 20 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        for patch in patches:
            if ApproxCountNonOverlappingRegionsInPatch(patch, 2, 2) < 3:
                return False
        return True
        
    params.get_valid_func = GetCastleSwordValid
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # castle sword 2
    rp = RoomPlacement()
    rp.room_id = 0x64
    
    # exit from castle sword 2 back to castle sword 1
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x14, 0x115))
    
    # exit from castle sword 2 to castle sword 3a
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x11, 0x1e, 0x11a))

    # exit from castle sword 2 to castle sword 3b
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x12, 0x1e, 0x119))

    # npcs 0-2
    for npc_addr in [0xa8e3, 0xa8e9, 0xa8ec]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    ######################################################################################
    # castle sword 1
    rp = RoomPlacement()
    rp.room_id = 0x63
    
    # exit from castle sword 1 back to the surface
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, 1], [-1, 1], [1, 1], [0, 2], [-1, 2], [1, 2]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x05, 0x05, MapChunkType.TILE, 0, 1, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = 0x0fc
    rep.exit_offset = [0, 0]
    rp.room_entrance_placements.append(rep)
    
    # exit from castle sword 1 to castle sword 2
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x11, 0x1e, 0x118))
    
    # npcs 0-2
    for npc_addr in [0xa8d4, 0xa8da, 0xa8dd]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    ######################################################################################
    # castle sword 3a
    rp = RoomPlacement()
    rp.room_id = 0x65
    
    # exit from castle sword 3a back to castle sword 2
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x15, 0x116))
    
    room_placements.append(rp)

    ######################################################################################
    # castle sword 3b
    rp = RoomPlacement()
    rp.room_id = 0x65
    
    # exit from castle sword 3b back to castle sword 2
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x14, 0x117))
    
    # npc (kingswrd)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa8f2
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    # copy position from kingswrd (alive) npc to kingswrd (dead) npc
    filebytes[0xa8f9] = filebytes[0xa8f2]
    filebytes[0xa8fa] = filebytes[0xa8f3]

    return

def RandomlyGenerateTower2FMap(filebytes):
    entrances = [[0x0a, 0x0bc, 0x017], [0x0c, 0x001, 0x018]]
    clone_exits = [0x001, 0x0bb]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xddbf, 84, 0x02, entrances, clone_exits)
    
def RandomlyGenerateTower3FMap(filebytes):
    entrances = [[0x0a, 0x0bd, 0x035], [0x0c, 0x002, 0x036], [0x0e, 0x0e9, 0x037]]
    clone_exits = [0x002, 0x0be]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xde13, 53, 0x03, entrances, clone_exits)
    
def RandomlyGenerateTower4FMap(filebytes):
    entrances = [[0x0a, 0x0c0, 0x058], [0x0c, 0x003, 0x059], [0x0e, 0x0ea, 0x05a]]
    clone_exits = [0x003, 0x0bf]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xde48, 96, 0x04, entrances, clone_exits)

def RandomlyGenerateFirstTowerSection(filebytes):
    # Randomly generate tower rooms
    room2f = RandomlyGenerateTower2FMap(filebytes)
    room3f = RandomlyGenerateTower3FMap(filebytes)
    room4f = RandomlyGenerateTower4FMap(filebytes)
    room5f = RandomlyGenerateTower5FMap(filebytes)

    # Randomize connections between tower rooms
    first_room = [[0xbb, 0x30, 0x15, 0x0d]]
    remaining_rooms = [room2f, room3f, room4f, room5f, \
        [[0x0bc, 0x31, 0x15, 0x14], [0x0bd, 0x31, 0x15, 0x0D]], \
        [[0x0be, 0x32, 0x15, 0x14], [0x0bf, 0x32, 0x15, 0x0D]], \
        [[0x0c0, 0x33, 0x15, 0x14], [0x0c1, 0x33, 0x15, 0x0D]], \
        [[0x0e9, 0x4a, 0x0d, 0x12]], \
        [[0x0ea, 0x4B, 0x09, 0x10]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)

    return

# Format for entrances: [0] top tile id, [1] return exit address, [2] outward exit address
# Format for clone_exits: source exit address, destination exit address
def RandomlyGenerateTowerRoomMap(filebytes, map_start_address, max_size_bytes, room_id, entrances, clone_exits):
    params = MakeTowerRoomParams()
    params.rooms_max_size_bytes = max_size_bytes - (1 + (5 * len(entrances)))
    params.map_start_address = map_start_address
    params.max_size_bytes = max_size_bytes
    room_placements = []
    rp = RoomPlacement()
    rp.room_id = room_id
    for entrance in entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    if random.randrange(0, 4) == 0:
        # Recovery spring
        rp.room_entrance_placements.append(MakeSingleTilePlacement(0x1b))
    room_placements.append(rp)
    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    exit_pos = GetExitPosition(filebytes, clone_exits[0])
    SetExitPosition(filebytes, clone_exits[1], exit_pos[0], exit_pos[1])
    
    # Read back exit positions and return exit data in "room" format for exit connection randomization
    exits = [GetExitPosition(filebytes, entrance[1]) for entrance in entrances]
    room_format_data = []
    for i in range(0, len(entrances)):
        room_format_data.append([entrances[i][2], room_id, exits[i][0], exits[i][1]])
    return room_format_data

def RandomlyGenerateTower5FMap(filebytes):
    map_start_address = 0xdea8
    max_size_bytes = 64
    room_id = 0x05
    crystal_door_entrance = [[0x0a, 0x0c2, 0x05b]]
    entrances = [[0x0c, 0x0c1, 0x05c]]
    non_return_data_entrances = [[0x0e, 0x11b, 0x05d]] # data for this entrance won't be returned from this function
    clone_exits = [0x0c1, 0x004]
    params = MakeTowerRoomParams()
    params.rooms_max_size_bytes = max_size_bytes - 21
    params.map_start_address = map_start_address
    params.max_size_bytes = max_size_bytes
    
    room_placements = []
    rp = RoomPlacement()
    rp.room_id = room_id
    for entrance in entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    for entrance in non_return_data_entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    if random.randrange(0, 5) == 0:
        # Recovery spring
        rp.room_entrance_placements.append(MakeSingleTilePlacement(0x1b))
    rp.room_entrance_placements.append(MakeCrystalDoorEntrancePlacement(0x0a, 0x15, 0x0c2, 0xa3aa))
    
    # npc (creator)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa3b1
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    exit_pos = GetExitPosition(filebytes, clone_exits[0])
    SetExitPosition(filebytes, clone_exits[1], exit_pos[0], exit_pos[1])
    
    # Read back exit positions and return exit data in "room" format for exit connection randomization
    exits = [GetExitPosition(filebytes, entrance[1]) for entrance in entrances]
    room_format_data = []
    for i in range(0, len(entrances)):
        room_format_data.append([entrances[i][2], room_id, exits[i][0], exits[i][1]])
    return room_format_data

def RandomlyGenerateOceanMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x01, 0x03, 0x04, 0x06, 0x07, 0x09, 0x0c, 0x0f, 0x11]
    params.map_fill_tile = 0x00 # ocean (island)
    params.backing_tile = 0x1e # jagged
    params.room_open_tile = random.choice([0x06, 0x0c, 0x0f, 0x11])
    params.chunk_tile_choices = [0x00, 0x01, 0x06, 0x0c, 0x0f, 0x11]
    params.rooms_max_size_bytes = 265
    params.map_start_address = 0xc148
    params.num_rooms = 17
    params.min_room_size = 4
    params.min_distance_between_rooms = 3
    params.min_room_y = 6
    params.max_size_bytes = 319
    
    def GetOceanValid(patches):
        if len(patches) != params.num_rooms:
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if any([len(patch) < 2 for patch in patches]):
            return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        for patch in patches:
            bb = GetPatchBoundingBox(patch)
            sides = [1+(bb[1][0]-bb[0][0]), 1+(bb[1][1]-bb[0][1])]
            if max(sides) / min(sides) > 2: # aspect ratio no greater than 2:1
                return False
        return True
        
    params.get_valid_func = GetOceanValid

    def MakeChunk():
        if random.randrange(0, 2) == 0:
            # random patch
            tile = random.choice(params.chunk_tile_choices)
            new_chunk = MapChunk()
            chunk_type = MapChunkType.CHECK
            new_chunk.Init(tile, tile, chunk_type, 0, 0, 0, 0)
            new_chunk.x_pos = random.randrange(0, MAP_X_MAX - 1)
            new_chunk.y_pos = random.randrange(0, MAP_Y_MAX - 1)
            new_chunk.x_size = random.randrange(1, min(int(0.5 * MAP_X_MAX), MAP_X_MAX - new_chunk.x_pos))
            new_chunk.y_size = random.randrange(1, min(int(0.5 * MAP_Y_MAX), MAP_Y_MAX - new_chunk.y_pos))
            return new_chunk
        else:
            # single tile floating island
            new_chunk = MapChunk()
            new_chunk.Init(0x03, 0x03, MapChunkType.TILE, 0, 0, 1, 1)
            new_chunk.x_pos = random.randrange(1, MAP_X_MAX - 1)
            new_chunk.y_pos = random.randrange(params.min_room_y, MAP_Y_MAX - 1)
            return new_chunk
            
    params.make_chunk_func = MakeChunk
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # tower, town, cave
    rp = RoomPlacement()
    rp.room_id = 0x66
    rep = RoomEntrancePlacement()
    new_chunk = MapChunk()
    new_chunk.Init(0x0a, 0x0b, MapChunkType.SQUARE, 0, -1, 1, 2)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = 0x5d
    rp.room_entrance_placements.append(rep)
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x15, 0x126))
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x12, 0x125))
    room_placements.append(rp)    
    
    ######################################################################################
    # airseed palm tree surrounded by forest
    rp = RoomPlacement()
    rp.room_id = 0x66
    rep = RoomEntrancePlacement()
    for x in range(-1, 1):
        for y in range(-3, 0):
            rep.non_walkable_tiles.append([x, y])
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x1d, 0x1d, MapChunkType.TILE, 0, -2, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = False
    new_chunk = MapChunk()
    new_chunk.Init(0x0c, 0x0c, MapChunkType.RING, -1, -3, 3, 3)
    rep.chunks.append(new_chunk)
    rp.room_entrance_placements.append(rep)
    room_placements.append(rp)

    ######################################################################################
    # cave, cave (connection between cave system 1 and cave system 2)
    rp = RoomPlacement()
    rp.room_id = 0x66
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x19, 0x12a))
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x17, 0x128))
    room_placements.append(rp)

    ######################################################################################
    # islands with caves: randomise which islands the caves appear on

    room_placements_with_random_caves = []
    remaining_caves = []
    remaining_caves.append(MakeSingleTilePlacementWithAddr(0x1b, 0x12c))
    remaining_caves.append(MakeSingleTilePlacementWithAddr(0x16, 0x127))
    remaining_caves.append(MakeSingleTilePlacementWithAddr(0x1a, 0x12b))
    remaining_caves.append(MakeSingleTilePlacementWithAddr(0x18, 0x129))
    remaining_caves.append(MakeSingleTilePlacementWithAddr(0x1c, 0x12d))
    
    for i in range(0, 4):
        rp = RoomPlacement()
        rp.room_id = 0x66
        room_placements_with_random_caves.append(rp)

    ######################################################################################
    # island vehicle
    rp = RoomPlacement()
    rp.room_id = 0x66
    rep = RoomEntrancePlacement()
    side_pick = random.randrange(4)
    if side_pick == 0:
        rep.non_walkable_tiles.append([-1, 0])
    if side_pick == 1:
        rep.non_walkable_tiles.append([1, 0])
    if side_pick == 2:
        rep.non_walkable_tiles.append([0, -1])
    if side_pick == 3:
        rep.non_walkable_tiles.append([0, 1])
    new_chunk = MapChunk()
    new_chunk.Init(0x1f, 0x1f, MapChunkType.TILE, 0, 0, 1, 1) #island vehicle
    rep.chunks.append(new_chunk)
    rp.room_entrance_placements.append(rep)
    # add a random remaining cave
    cave_choice = random.choice(remaining_caves)
    rp.room_entrance_placements.append(cave_choice)
    remaining_caves.remove(cave_choice)
    room_placements.append(rp)
    
    for cave in remaining_caves:
        rp = random.choice(room_placements_with_random_caves)
        rp.room_entrance_placements.append(cave)
        
    for rp in room_placements_with_random_caves:
        if len(rp.room_entrance_placements) > 0:
            room_placements.append(rp)

    ######################################################################################
    # town
    rp = RoomPlacement()
    rp.room_id = 0x66
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x13, 0x12e))
    room_placements.append(rp)

    ######################################################################################
    # hut
    rp = RoomPlacement()
    rp.room_id = 0x66
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x14, 0x12f))
    room_placements.append(rp)

    params.room_placements = room_placements
    
    ######################################################################################
    # whirlpool
    whirlpool_placement = MakeSingleTilePlacementWithAddr(0x0e, 0x130)
    new_chunk = MapChunk()
    new_chunk.Init(0x00, 0x00, MapChunkType.CHECK, -1, -1, 3, 3) # 3x3 square of ocean
    whirlpool_placement.chunks.insert(0, new_chunk) # inserted before the whirlpool tile, so below/behind it
    whirlpool_placement.non_walkable_tiles = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]]
    whirlpool_placement.exit_offset = [0, 1]
    params.non_walkable_area_placements.append(whirlpool_placement)
    params.non_walkable_area_placements_room_id = 0x66
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return

def MakeTowerRoomParams():
    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x09, 0x16, 0x18, 0x19, 0x1a, 0x1d]
    params.map_fill_tile = 0x01 # med brick
    params.backing_tile = 0x1e # light block
    params.room_open_tile = 0x1a
    # tile choices: 
    params.chunk_tile_choices = ([0x01] * 5) + [0x16] + [0x1a, 0x1d] # bricks, stairs
    params.num_rooms = 1
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.chunks_must_change_walkable = True
    
    style_pick = random.randrange(0, 5)
    if style_pick == 1:
        # grass, 5F-style blocks
        params.map_fill_tile = 0x03
        params.room_open_tile = 0x18
        params.chunk_tile_choices = ([0x03] * 5) + [0x16] + ([0x18] * 3)
    if style_pick == 2:
        # girders
        params.map_fill_tile = 0x07
        params.room_open_tile = 0x1a
        params.chunk_tile_choices = ([0x07] * 5) + [0x16] + ([0x1a] * 3)
    if style_pick == 3:
        # clouds, stairs, grass
        params.map_fill_tile = 0x11
        params.room_open_tile = 0x18
        params.chunk_tile_choices = ([0x11] * 5) + [0x16] + [0x18, 0x1d]
    if style_pick == 4:
        # water, dark stairs
        params.map_fill_tile = 0x10
        params.room_open_tile = 0x19
        params.chunk_tile_choices = ([0x10] * 5) + [0x16] + ([0x19] * 3)
    
    def GetTowerRoomValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 20 for patch in patches]):
            return False
        return True
        
    params.get_valid_func = GetTowerRoomValid
    
    return params

class RoomEntrancePlacement:
    def __init__(self):
        # list of required non walkable tiles, each of which is a relative cell position, which is a two member list
        # eg [0, 1] means the tile at [x, y+1] is required to be non-walkable
        self.non_walkable_tiles = []
        # list of MapChunks which will be added, each with relative positions
        self.chunks = []
        self.write_exit = False
        # address of exit data which will be written
        self.exit_addr = 0
        # x, y offset of exit data
        self.exit_offset = [0, 0]
        # x, y offset of npc position
        self.exit_npc_pos_offset = [0, 0]
        # start addresses for positions of npcs which need to have the same position as the exit
        self.exit_npc_pos_start_addr = []
    
class RoomNPCPlacement:
    def __init__(self):
        # list of cells required to be in the cell list, each of which is a relative cell position, which is a two member list
        # eg [0, 1] means the tile at [x, y+1] is required to be in the cell list
        self.required_cells = []
        # start address for position
        self.pos_start_addr = 0
    
class RoomPlacement:
    def __init__(self):
        self.room_id = 0
        self.remaining_cells = []
        self.room_entrance_placements = []
        self.room_npc_placements = []
    
def MakeStairsUpEntrancePlacement(stairs_tile, hole_tile, exit_addr):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2], [0, -3], [-1, -3], [1, -3]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(stairs_tile, stairs_tile, MapChunkType.TILE, 0, -1, 1, 1)
    rep.chunks.append(new_chunk)
    new_chunk = MapChunk()
    new_chunk.Init(hole_tile, hole_tile, MapChunkType.TILE, 0, -2, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep
    
def MakeStairsDownEntrancePlacement(stairs_tile, exit_addr):
    # exit from bandit cave 1 to bandit cave 2
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, 1], [-1, 1], [1, 1], [0, 2], [-1, 2], [1, 2]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(stairs_tile, stairs_tile, MapChunkType.TILE, 0, 1, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep
    
def MakeDoorEntrancePlacement(door_tile, door_bottom_tile):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2], [0, -3], [-1, -3], [1, -3]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(door_bottom_tile, door_bottom_tile, MapChunkType.TILE, 0, -2, 1, 1)
    rep.chunks.append(new_chunk)
    new_chunk = MapChunk()
    new_chunk.Init(door_tile, door_tile, MapChunkType.TILE, 0, -1, 1, 1)
    rep.chunks.append(new_chunk)
    return rep
    
def MakeWarpBackDoorEntrancePlacement(door_bottom_tile, exit_addr):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, 1], [-1, 1], [1, 1], [0, 2], [-1, 2], [1, 2], [0, 3], [-1, 3], [1, 3]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(door_bottom_tile, door_bottom_tile, MapChunkType.SQUARE, 0, 1, 1, 2)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep
    
def MakeOnePieceDoorEntrancePlacement(door_top_tile, exit_addr):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2], [0, -3], [-1, -3], [1, -3]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(door_top_tile, door_top_tile, MapChunkType.SQUARE, 0, -2, 1, 2)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep
    
def MakeOnePieceDoorEntrancePlacementWithoutAddr(door_top_tile):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2], [0, -3], [-1, -3], [1, -3]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(door_top_tile, door_top_tile, MapChunkType.SQUARE, 0, -2, 1, 2)
    rep.chunks.append(new_chunk)
    rep.write_exit = False
    return rep

def MakeSingleTilePlacement(tile):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = []
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(tile, tile, MapChunkType.TILE, 0, 0, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = False
    return rep
    
def MakeCrystalDoorEntrancePlacement(door_top_tile, crystal_insignia_tile, exit_addr, npc_addr):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, -1], [-1, -1], [1, -1], [0, -2], [-1, -2], [1, -2], [0, -3], [-1, -3], [1, -3], [0, -4], [-1, -4], [1, -4]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(door_top_tile, door_top_tile, MapChunkType.SQUARE, 0, -2, 1, 2)
    rep.chunks.append(new_chunk)
    new_chunk = MapChunk()
    new_chunk.Init(crystal_insignia_tile, crystal_insignia_tile, MapChunkType.TILE, 0, -3, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    rep.exit_npc_pos_offset = [0, -1]
    rep.exit_npc_pos_start_addr.append(npc_addr)
    return rep
    
def MakeSingleTilePlacementWithAddr(tile, exit_addr):
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = []
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(tile, tile, MapChunkType.TILE, 0, 0, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep    

def MakeOutsideDustRoomPlacement(tile, exit_addr):    
    # exit from castle sword 1 back to the surface
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[0, 1], [-1, 1], [1, 1], [0, 2], [-1, 2], [1, 2]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(tile, tile, MapChunkType.TILE, 0, 1, 1, 1)
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = exit_addr
    rep.exit_offset = [0, 0]
    return rep
    
def GetMinDistanceBetweenPatches(patch_a, patch_b):
    return min([GetDistanceBetweenCells(cell_a, cell_b) for cell_a in patch_a for cell_b in patch_b])
    
def GetDistanceBetweenCells(cell_a, cell_b):
    x = abs(cell_a[0] - cell_b[0])
    y = abs(cell_a[1] - cell_b[1])
    return math.sqrt((x*x) + (y*y))
    
def GetAllPatchesAreDistanceApart(patches, min_distance):
    for patch_i in range(0, len(patches) - 1):
        for patch_j in range(patch_i + 1, len(patches)):
            if GetMinDistanceBetweenPatches(patches[patch_i], patches[patch_j]) < min_distance:
                return False
    return True
    
def GetPatchBoundingBox(patch):
    patch_min = [min([cell[0] for cell in patch]), min([cell[1] for cell in patch])]
    patch_max = [max([cell[0] for cell in patch]), max([cell[1] for cell in patch])]
    # print("GetPatchBoundingBox", patch_min, patch_max)
    return [patch_min, patch_max]
    
def ApproxCountNonOverlappingRegionsInPatch(patch, region_x, region_y):
    copy_patch = list(patch)
    num_regions = 0
    while True:
        loc = FindFirstRegionInCellList(copy_patch, region_x, region_y)
        if len(loc) != 2:
            # failed to find region                                
            break
        num_regions += 1
        # remove region from patch
        for x_offset in range(0, region_x):
            for y_offset in range(0, region_y):
                remove_cell = [loc[0] + x_offset, loc[1] + y_offset]
                copy_patch.remove([loc[0] + x_offset, loc[1] + y_offset])
    return num_regions
    
def FindFirstRegionInCellList(cell_list, region_x, region_y):
    for cell in cell_list:
        valid = True
        for x_off in range(0, region_x):
            for y_off in range(0, region_y):
                if not [cell[0] + x_off, cell[1] + y_off] in cell_list:
                    valid = False
                    break
            if not valid:
                break
        if valid:
            return cell
    return []
    
def RemoveIneffectiveChunks(chunks, backing_tile):
    map_cols = [[backing_tile for y in range(0, MAP_Y_MAX + 1)] for x in range(0, MAP_X_MAX + 1)]
    EvaluateMap(map_cols, chunks, backing_tile)
    test_map_cols = [[backing_tile for y in range(0, MAP_Y_MAX + 1)] for x in range(0, MAP_X_MAX + 1)]
    for chunk_idx in range(len(chunks) - 1, -1, -1):
        test_chunks = list(chunks)
        del(test_chunks[chunk_idx])
        EvaluateMap(test_map_cols, test_chunks, backing_tile)
        keep_chunk = False
        for x in range(0, MAP_X_MAX + 1):
            for y in range(0, MAP_Y_MAX + 1):
                if map_cols[x][y] != test_map_cols[x][y]:
                    keep_chunk = True
                    break
            if keep_chunk:
                break
        if not keep_chunk:
            del(chunks[chunk_idx])
    return
    
def RandomlyGenerateOceanCaves1Map(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x02, 0x03, 0x04, 0x05, 0x17, 0x19, 0x1a, 0x1b, 0x1d]
    params.map_fill_tile = 0x00
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x1d # green (open)
    params.chunk_tile_choices = [0x1d, 0x00]
    params.rooms_max_size_bytes = 47
    params.map_start_address = 0xd05e
    params.num_rooms = 1
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 72
    
    def GetCaveValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        return True
        
    params.get_valid_func = GetCaveValid
    
    # define data
    room_placements = []
    
    rp = RoomPlacement()
    rp.room_id = 0x68
    
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x06, 0x1e, 0x11d))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x07, 0x1e, 0x11e))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x08, 0x1e, 0x11f))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x09, 0x1e, 0x120))
    
    room_placements.append(rp)
    
    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return

def RandomlyGenerateOceanCaves2Map(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x02, 0x03, 0x04, 0x05, 0x17, 0x19, 0x1a, 0x1b, 0x1d]
    params.map_fill_tile = 0x00
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x1d # green (open)
    params.chunk_tile_choices = [0x1d, 0x00]
    params.rooms_max_size_bytes = 81
    params.map_start_address = 0xd0a6
    params.num_rooms = 1
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 107
    
    def GetCaveValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        return True
        
    params.get_valid_func = GetCaveValid
    
    # define data
    
    rp = RoomPlacement()
    rp.room_id = 0x69
    
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x06, 0x1e, 0x121))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x07, 0x1e, 0x122))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x08, 0x1e, 0x123))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x09, 0x1e, 0x124))
    
    params.room_placements.append(rp)
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return
    
def RandomlyGenerateUnderseaMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x01, 0x0b, 0x12, 0x13, 0x14, 0x15, 0x17, 0x19, 0x1a, 0x1e]
    params.map_fill_tile = 0x1d
    params.backing_tile = 0x1e
    params.room_open_tile = 0x01
    params.chunk_tile_choices = [0x01] + ([0x1d] * 5)
    params.rooms_max_size_bytes = 41
    params.map_start_address = 0xd191
    params.num_rooms = 3
    params.min_room_size = 20
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 65
    
    def GetUnderseaValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 20 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        for patch in patches:
            if ApproxCountNonOverlappingRegionsInPatch(patch, 2, 2) < 1:
                return False
        return True
        
    params.get_valid_func = GetUnderseaValid
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # seabed 2
    rp = RoomPlacement()
    rp.room_id = 0x71
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x07, 0x137)) # stairs
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = []
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x02, 0x02, MapChunkType.SQUARE, 0, 0, 2, 2) # dragon palace
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = 0x13c
    rep.exit_offset = [0, 1]
    rp.room_entrance_placements.append(rep)
    
    room_placements.append(rp)

    ######################################################################################
    # seabed 2
    rp = RoomPlacement()
    rp.room_id = 0x70
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x07, 0x136)) # stairs
    room_placements.append(rp)

    ######################################################################################
    # seabed 1
    rp = RoomPlacement()
    rp.room_id = 0x6c
    
    # back to the surface
    rep = RoomEntrancePlacement()
    rep.non_walkable_tiles = [[1, 0], [1, -1], [1, 1], [2, 0], [2, -1], [2, 1], [3, 0], [3, -1], [3, 1]]
    rep.chunks = []
    new_chunk = MapChunk()
    new_chunk.Init(0x13, 0x13, MapChunkType.TILE, 1, 0, 1, 1) # horizontal bridge
    rep.chunks.append(new_chunk)
    new_chunk = MapChunk()
    new_chunk.Init(0x1b, 0x1b, MapChunkType.TILE, 2, 0, 1, 1) # whirlpool
    rep.chunks.append(new_chunk)
    rep.write_exit = True
    rep.exit_addr = 0x22
    rep.exit_offset = [1, 0]
    rp.room_entrance_placements.append(rep)
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x06, 0x132)) # town
    rp.room_entrance_placements.append(MakeSingleTilePlacementWithAddr(0x07, 0x133)) # stairs

    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    # copy position from exit 0x13c to 0x44
    exit_pos = GetExitPosition(filebytes, 0x13c)
    SetExitPosition(filebytes, 0x44, exit_pos[0], exit_pos[1])
    
    return
    
def RandomlyGenerateUnderseaCavesMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x02, 0x03, 0x04, 0x05, 0x19, 0x1a, 0x1b, 0x1d]
    params.map_fill_tile = 0x00
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x1d # green (open)
    params.chunk_tile_choices = [0x00, 0x1d]
    params.rooms_max_size_bytes = 100
    params.map_start_address = 0xd111
    params.num_rooms = 2
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 128
    
    def GetUnderseaCaveValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 80 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        return True
        
    params.get_valid_func = GetUnderseaCaveValid
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # undersea cave 2
    rp = RoomPlacement()
    rp.room_id = 0x6f
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x07, 0x1e, 0x134))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x09, 0x1e, 0x13a))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x08, 0x1e, 0x138))
    room_placements.append(rp)
    
    ######################################################################################
    # undersea cave 1
    rp = RoomPlacement()
    rp.room_id = 0x6e
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x06, 0x1e, 0x131))
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x0a, 0x135))
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return

def MakeDragonPalaceChunk():
    tile_choices = [0x04] + ([0x01, 0x03, 0x0d] * 3)
    min_room_y = 6
    if random.randrange(0, 10) == 0:
        # single tile fake orb
        new_chunk = MapChunk()
        new_chunk.Init(0x08, 0x08, MapChunkType.TILE, 0, 0, 1, 1)
        new_chunk.x_pos = random.randrange(1, MAP_X_MAX - 1)
        new_chunk.y_pos = random.randrange(min_room_y, MAP_Y_MAX - 1)
        return new_chunk
    else:
        # random patch or ring
        tile = random.choice(tile_choices)
        new_chunk = MapChunk()
        chunk_type = MapChunkType.RING
        if random.randrange(0, 3) == 0:
            chunk_type = MapChunkType.CHECK
        new_chunk.Init(tile, tile, chunk_type, 0, 0, 0, 0)
        new_chunk.x_pos = random.randrange(0, MAP_X_MAX - 1)
        new_chunk.y_pos = random.randrange(0, MAP_Y_MAX - 1)
        new_chunk.x_size = random.randrange(1, min(int(0.5 * MAP_X_MAX), MAP_X_MAX - new_chunk.x_pos))
        new_chunk.y_size = random.randrange(1, min(int(0.5 * MAP_Y_MAX), MAP_Y_MAX - new_chunk.y_pos))
        return new_chunk

def RandomlyGenerateDragonPalaceMap(filebytes):
    RandomlyGenerateDragonPalace123Map(filebytes)
    RandomlyGenerateDragonPalace4Map(filebytes)
    RandomlyGenerateSeiRyuRoomMap(filebytes)
    RandomlyGenerateDragonPalaceRoomsMap(filebytes)
    
    # randomly permute exits to locked rooms
    one_way_exits = []
    exit_addrs = [0x13f, 0x142, 0x145]
    for exit_addr in exit_addrs:
        start_addr = 0x92d0 + (exit_addr * 3)
        exit_data = list(filebytes[start_addr:start_addr+3])
        one_way_exits.append([exit_addr] + exit_data)
    RandomlyPermuteOneWayExits(one_way_exits)
    WriteOneWayExits(filebytes, one_way_exits)
    
    return
        
def RandomlyGenerateDragonPalace123Map(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x03, 0x04, 0x07, 0x08, 0x0a, 0x0b, 0x0e, 0x0f, 0x10]
    params.map_fill_tile = 0x01
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x03
    params.chunk_tile_choices = [0x01, 0x03, 0x04, 0x0d]
    params.rooms_max_size_bytes = 263
    params.map_start_address = 0xcdbb
    params.num_rooms = 3
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 306
    
    def GetDragonPalaceValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 40 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        for patch in patches:
            if ApproxCountNonOverlappingRegionsInPatch(patch, 2, 2) < 3:
                return False
        return True
        
    params.get_valid_func = GetDragonPalaceValid
    
    params.make_chunk_func = MakeDragonPalaceChunk
    
    params.chunks_must_change_walkable = True
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # dragon palace 1
    rp = RoomPlacement()
    rp.room_id = 0x72
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x11, 0x1e, 0x140))
    rp.room_entrance_placements.append(MakeOutsideDustRoomPlacement(0x05, 0x139))
    rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacementWithoutAddr(0x17))
    
    # npcs 0-2
    for npc_addr in [0xa98f, 0xa995, 0xa998]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)
    
    ######################################################################################
    # dragon palace 2
    rp = RoomPlacement()
    rp.room_id = 0x73
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x14, 0x13d))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x12, 0x1e, 0x143))
    door_placement = MakeOnePieceDoorEntrancePlacementWithoutAddr(0x19)
    door_placement.exit_npc_pos_start_addr.append(0xa9ab) # BLUEKEY check
    door_placement.exit_npc_pos_offset = [0, -1]
    rp.room_entrance_placements.append(door_placement)

    # npcs 0-2
    for npc_addr in [0xa99e, 0xa9a4, 0xa9a7]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    ######################################################################################
    # dragon palace 3
    rp = RoomPlacement()
    rp.room_id = 0x74
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x15, 0x13e))
    rp.room_entrance_placements.append(MakeStairsUpEntrancePlacement(0x13, 0x1e, 0x144))
    door_placement = MakeOnePieceDoorEntrancePlacementWithoutAddr(0x1b)
    door_placement.exit_npc_pos_start_addr.append(0xa9c1) # BLUEKEY check
    door_placement.exit_npc_pos_offset = [0, -1]
    rp.room_entrance_placements.append(door_placement)

    # npcs 0-2
    for npc_addr in [0xa9b4, 0xa9ba, 0xa9bd]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return

def RandomlyGenerateDragonPalace4Map(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x03, 0x04, 0x07, 0x08, 0x0a, 0x0b, 0x0e, 0x0f, 0x10]
    params.map_fill_tile = 0x01
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x03
    params.chunk_tile_choices = [0x01, 0x03, 0x04, 0x0d]
    params.rooms_max_size_bytes = 41
    params.map_start_address = 0xceed
    params.num_rooms = 1
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 51
    
    def GetDragonPalaceValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 40 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        return True
        
    params.get_valid_func = GetDragonPalaceValid
    
    params.make_chunk_func = MakeDragonPalaceChunk
    
    params.chunks_must_change_walkable = True
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # dragon palace 4
    rp = RoomPlacement()
    rp.room_id = 0x75
    rp.room_entrance_placements.append(MakeStairsDownEntrancePlacement(0x14, 0x141))
    door_placement = MakeOnePieceDoorEntrancePlacementWithoutAddr(0x17)
    door_placement.exit_npc_pos_start_addr.append(0xa9ca) # BLUEKEY check
    door_placement.exit_npc_pos_offset = [0, -1]
    rp.room_entrance_placements.append(door_placement)

    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)

    return

def RandomlyGenerateSeiRyuRoomMap(filebytes):

    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x03, 0x04, 0x07, 0x08, 0x0a, 0x0b, 0x0e, 0x0f, 0x10]
    params.map_fill_tile = 0x01
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x03
    params.chunk_tile_choices = [0x01, 0x03, 0x04, 0x0d]
    params.rooms_max_size_bytes = 52
    params.map_start_address = 0xcf63
    params.num_rooms = 1
    params.min_room_size = 0x20
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 61
    
    def GetDragonPalaceValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 40 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        return True
        
    params.get_valid_func = GetDragonPalaceValid
    
    def MakeSeiRyuRoomChunk():
        tile_choices = [0x04] + ([0x01, 0x03, 0x0d] * 3)
        min_room_y = 6
        if random.randrange(0, 3) == 0:
            # single tile fake orb
            new_chunk = MapChunk()
            new_chunk.Init(0x08, 0x08, MapChunkType.TILE, 0, 0, 1, 1)
            new_chunk.x_pos = random.randrange(1, MAP_X_MAX - 1)
            new_chunk.y_pos = random.randrange(min_room_y, MAP_Y_MAX - 1)
            return new_chunk
        else:
            # random patch or ring
            tile = random.choice(tile_choices)
            new_chunk = MapChunk()
            chunk_type = MapChunkType.RING
            if random.randrange(0, 3) == 0:
                chunk_type = MapChunkType.CHECK
            new_chunk.Init(tile, tile, chunk_type, 0, 0, 0, 0)
            new_chunk.x_pos = random.randrange(0, MAP_X_MAX - 1)
            new_chunk.y_pos = random.randrange(0, MAP_Y_MAX - 1)
            new_chunk.x_size = random.randrange(1, min(int(0.5 * MAP_X_MAX), MAP_X_MAX - new_chunk.x_pos))
            new_chunk.y_size = random.randrange(1, min(int(0.5 * MAP_Y_MAX), MAP_Y_MAX - new_chunk.y_pos))
            return new_chunk
    
    params.make_chunk_func = MakeSeiRyuRoomChunk
    
    params.chunks_must_change_walkable = False
    
    head_npc_placement_addr = 0xa9d3
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # sei-ryu's room
    rp = RoomPlacement()
    rp.room_id = 0x76
    orb_placement = MakeSingleTilePlacement(0x10) # sei-ryu's orb
    orb_placement.exit_npc_pos_start_addr.append(head_npc_placement_addr)
    orb_placement.exit_npc_pos_offset = [0, 0]
    rp.room_entrance_placements.append(orb_placement)
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x17, 0x145))

    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    # set npc positions for Sei-Ryu's other three segments
    head_pos = [filebytes[head_npc_placement_addr], filebytes[head_npc_placement_addr+1]]
    filebytes[0xa9da] = head_pos[0]
    filebytes[0xa9db] = head_pos[1] - 1
    filebytes[0xa9e1] = head_pos[0] + 1
    filebytes[0xa9e2] = head_pos[1] - 1
    filebytes[0xa9e8] = head_pos[0] + 1
    filebytes[0xa9e9] = head_pos[1] - 2

    return
    
def RandomlyGenerateDragonPalaceRoomsMap(filebytes):
    params = MultiRoomDungeonParams()
    
    params.walkable_tiles = [0x00, 0x03, 0x04, 0x07, 0x08, 0x0a, 0x0b, 0x0e, 0x0f, 0x10]
    params.map_fill_tile = 0x01
    params.backing_tile = 0x1e # black square
    params.room_open_tile = 0x03
    params.chunk_tile_choices = [0x01, 0x03, 0x04, 0x0d]
    params.rooms_max_size_bytes = 51
    params.map_start_address = 0xcf20
    params.num_rooms = 3
    params.min_room_size = 9
    params.min_distance_between_rooms = 6
    params.min_room_y = 6
    params.max_size_bytes = 67
    
    def GetDragonPalaceValid(patches):
        if not len(patches) == params.num_rooms:
            return False
        if not all([len(patch) >= 40 for patch in patches]):
            return False
        for patch in patches:
            if any([cell[1] < params.min_room_y for cell in patch]):
                return False
        if not GetAllPatchesAreDistanceApart(patches, params.min_distance_between_rooms):
            return False
        return True
        
    params.get_valid_func = GetDragonPalaceValid
    
    params.make_chunk_func = MakeDragonPalaceChunk
    
    params.chunks_must_change_walkable = True
    
    # define data
    
    room_placements = []
    
    ######################################################################################
    # dragon treasure room
    rp = RoomPlacement()
    rp.room_id = 0x77
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x19, 0x142))
    
    for npc_addr in [0xa9f1, 0xa9f8, 0xa9ff]:
        rnp = RoomNPCPlacement()
        rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
        rnp.pos_start_addr = npc_addr
        rp.room_npc_placements.append(rnp)

    room_placements.append(rp)

    ######################################################################################
    # dragon key room
    rp = RoomPlacement()
    rp.room_id = 0x79
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x1b, 0x13b))
    
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [-1, 0], [1, 0], [0, 1], [-1, 1], [1, 1]]
    rnp.pos_start_addr = 0xaa08
    rp.room_npc_placements.append(rnp)

    room_placements.append(rp)

    ######################################################################################
    # dragon empty room
    rp = RoomPlacement()
    rp.room_id = 0x78
    rp.room_entrance_placements.append(MakeWarpBackDoorEntrancePlacement(0x17, 0x13f))
    
    room_placements.append(rp)

    params.room_placements = room_placements

    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    # copy npc positions for key room chests
    chest_pos = [filebytes[0xaa08], filebytes[0xaa09]]
    for dest_addr in [0xaa0f, 0xaa16, 0xaa1d]:
        filebytes[dest_addr] = chest_pos[0]
        filebytes[dest_addr+1] = chest_pos[1]

    return
    
def RandomlyGenerateSecondTowerSection(filebytes):
    # Randomly generate tower rooms
    room6f = RandomlyGenerateTower6FMap(filebytes)
    room7f = RandomlyGenerateTower7FMap(filebytes)
    room8f = RandomlyGenerateTower8FMap(filebytes)
    room9f = RandomlyGenerateTower9FMap(filebytes)
    room10f = RandomlyGenerateTower10FMap(filebytes)

    # Randomize connections between tower rooms
    floor_5_pos = GetExitPosition(filebytes, 0xc2)
    first_room = [[0x05b, 0x05, floor_5_pos[0], floor_5_pos[1]]]
    remaining_rooms = [room6f, room7f, room8f, room9f, room10f, \
            [[0x0c2, 0x34, 0x33, 0x14], [0x0c3, 0x34, 0x33, 0x0d]], \
            [[0x0c4, 0x35, 0x33, 0x14], [0x0c5, 0x35, 0x33, 0x0d]], \
            [[0x0c6, 0x36, 0x33, 0x14], [0x0c7, 0x36, 0x33, 0x0d]], \
            [[0x0c8, 0x37, 0x33, 0x14], [0x0c9, 0x37, 0x33, 0x0d]], \
            [[0x0ca, 0x38, 0x33, 0x14], [0x0cb, 0x38, 0x33, 0x0d]], \
            [[0x0eb, 0x4c, 0x15, 0x23]], \
            [[0x0ec, 0x4d, 0x13, 0x0c]] \
            ]        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)

    return
    
def RandomlyGenerateTower6FMap(filebytes):
    entrances = [[0x0a, 0x0c4, 0x03a], [0x0c, 0x0c3, 0x03b]]
    clone_exits = [0x0c3, 0x005]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xdee8, 59, 0x06, entrances, clone_exits)

def RandomlyGenerateTower7FMap(filebytes):
    entrances = [[0x0e, 0x0eb, 0x060], [0x0a, 0x0c6, 0x05e], [0x0c, 0x0c5, 0x05f]]
    clone_exits = [0x0c5, 0x006]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xdf23, 83, 0x07, entrances, clone_exits)
    
def RandomlyGenerateTower8FMap(filebytes):
    entrances = [[0x0c, 0x0c7, 0x04e], [0x0a, 0x0c8, 0x04d]]
    clone_exits = [0x0c7, 0x007]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xdf76, 75, 0x08, entrances, clone_exits)

def RandomlyGenerateTower9FMap(filebytes):
    entrances = [[0x0c, 0x0c9, 0x062], [0x0a, 0x0ca, 0x061], [0x0e, 0x0ec, 0x063]]
    clone_exits = [0x0c9, 0x008]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xdfc1, 93, 0x09, entrances, clone_exits)
    
def RandomlyGenerateTower10FMap(filebytes):
    map_start_address = 0xe01e
    max_size_bytes = 125
    room_id = 0x0a
    crystal_door_entrance = [[0x0a, 0x0cc, 0x064]]
    entrances = [[0x0c, 0x0cb, 0x065]]
    non_return_data_entrances = [[0x0e, 0x146, 0x066]] # data for this entrance won't be returned from this function
    clone_exits = [0x0cb, 0x009]
    params = MakeTowerRoomParams()
    params.rooms_max_size_bytes = max_size_bytes - 21
    params.map_start_address = map_start_address
    params.max_size_bytes = max_size_bytes
    
    room_placements = []
    rp = RoomPlacement()
    rp.room_id = room_id
    for entrance in entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    for entrance in non_return_data_entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    if random.randrange(0, 5) == 0:
        # Recovery spring
        rp.room_entrance_placements.append(MakeSingleTilePlacement(0x1b))
    rp.room_entrance_placements.append(MakeCrystalDoorEntrancePlacement(crystal_door_entrance[0][0], 0x15, crystal_door_entrance[0][1], 0xa3ba))
    
    # npc (creator)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa3c1
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    exit_pos = GetExitPosition(filebytes, clone_exits[0])
    SetExitPosition(filebytes, clone_exits[1], exit_pos[0], exit_pos[1])
    
    # Read back exit positions and return exit data in "room" format for exit connection randomization
    exits = [GetExitPosition(filebytes, entrance[1]) for entrance in entrances]
    room_format_data = []
    for i in range(0, len(entrances)):
        room_format_data.append([entrances[i][2], room_id, exits[i][0], exits[i][1]])
    return room_format_data
    
def RandomlyGenerateThirdTowerSection(filebytes):
    # Randomly generate tower rooms
    room11f = RandomlyGenerateTower11FMap(filebytes)
    room12f = RandomlyGenerateTower12FMap(filebytes)
    room13f = RandomlyGenerateTower13FMap(filebytes)
    room14f = RandomlyGenerateTower14FMap(filebytes)
    room15f = RandomlyGenerateTower15FMap(filebytes)
    room16f = RandomlyGenerateTower16FMap(filebytes)
    
    # Randomize connections between tower rooms
    floor_10_pos = GetExitPosition(filebytes, 0xcc)
    first_room = [[0x064, 0x0a, floor_10_pos[0], floor_10_pos[1]]]
    remaining_rooms = [room11f, room12f, room13f, room14f, room15f, room16f, \
        [[0x0cc, 0x39, 0x15, 0x14], [0x0cd, 0x39, 0x15, 0x0d]], \
        [[0x0ce, 0x3a, 0x15, 0x14], [0x0cf, 0x3a, 0x15, 0x0d]], \
        [[0x0d0, 0x3b, 0x15, 0x14], [0x0d1, 0x3b, 0x15, 0x0d]], \
        [[0x0d2, 0x3c, 0x15, 0x14], [0x0d3, 0x3c, 0x15, 0x0d]], \
        [[0x0d4, 0x3d, 0x15, 0x14], [0x0d5, 0x3d, 0x15, 0x0d]], \
        [[0x0d6, 0x3e, 0x15, 0x14], [0x0d7, 0x3e, 0x15, 0x0d]], \
        [[0x0ed, 0x4e, 0x20, 0x10]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)

    return
    
def RandomlyGenerateTower11FMap(filebytes):
    entrances = [[0x0a, 0x0ce, 0x067], [0x0c, 0x0cd, 0x068]]
    clone_exits = [0x0cd, 0x00a]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe09b, 95, 0x0b, entrances, clone_exits)
    
def RandomlyGenerateTower12FMap(filebytes):
    entrances = [[0x0c, 0x0cf, 0x06a], [0x0a, 0x0d0, 0x069], [0x0e, 0x0ed, 0x06b]]
    clone_exits = [0x0cf, 0x00b]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe0fa, 106, 0x0c, entrances, clone_exits)

def RandomlyGenerateTower13FMap(filebytes):
    entrances = [[0x0c, 0x0d1, 0x06d], [0x0a, 0x0d2, 0x06c], [0x0e, 0x0ee, 0x06e]]
    clone_exits = [0x0d1, 0x00c]
    exits = RandomlyGenerateTowerRoomMap(filebytes, 0xe164, 100, 0x0d, entrances, clone_exits)
    # Set position of drowned/flooded world exit
    SetExitPosition(filebytes, entrances[2][1], exits[2][2], exits[2][3])
    # Copy position of extra exit for drowned/flooded world
    exit_pos = GetExitPosition(filebytes, 0x0ee)
    SetExitPosition(filebytes, 0x0f6, exit_pos[0], exit_pos[1])
    return exits[:2] # Don't randomize connection to drowned/flooded world

def RandomlyGenerateTower14FMap(filebytes):
    entrances = [[0x0c, 0x0d3, 0x071], [0x0a, 0x0d4, 0x070], [0x0e, 0x0ef, 0x072]]
    clone_exits = [0x0d3, 0x00d]
    exits = RandomlyGenerateTowerRoomMap(filebytes, 0xe1c8, 94, 0x0e, entrances, clone_exits)
    # Set position of drowned/flooded world exit
    SetExitPosition(filebytes, entrances[2][1], exits[2][2], exits[2][3])
    # Copy position of extra exit for drowned/flooded world
    exit_pos = GetExitPosition(filebytes, 0x0ef)
    SetExitPosition(filebytes, 0x0f7, exit_pos[0], exit_pos[1])
    return exits[:2] # Don't randomize connection to drowned/flooded world

def RandomlyGenerateTower15FMap(filebytes):
    entrances = [[0x0c, 0x0d5, 0x075], [0x0a, 0x0d6, 0x074]]
    clone_exits = [0x0d5, 0x00e]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe226, 92, 0x0f, entrances, clone_exits)

def RandomlyGenerateTower16FMap(filebytes):
    map_start_address = 0xe282
    max_size_bytes = 86
    room_id = 0x10
    crystal_door_entrance = [[0x0a, 0x0d8, 0x076]]
    entrances = [[0x0c, 0x0d7, 0x077]]
    non_return_data_entrances = [[0x0e, 0x08c, 0x078]] # data for this entrance won't be returned from this function
    clone_exits = [0x0d7, 0x00f]
    params = MakeTowerRoomParams()
    params.rooms_max_size_bytes = max_size_bytes - 21
    params.map_start_address = map_start_address
    params.max_size_bytes = max_size_bytes
    
    room_placements = []
    rp = RoomPlacement()
    rp.room_id = room_id
    for entrance in entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    for entrance in non_return_data_entrances:
        rp.room_entrance_placements.append(MakeOnePieceDoorEntrancePlacement(entrance[0], entrance[1]))
    if random.randrange(0, 5) == 0:
        # Recovery spring
        rp.room_entrance_placements.append(MakeSingleTilePlacement(0x1b))
    rp.room_entrance_placements.append(MakeCrystalDoorEntrancePlacement(crystal_door_entrance[0][0], 0x15, crystal_door_entrance[0][1], 0xa3ca))
    
    # npc (creator)
    rnp = RoomNPCPlacement()
    rnp.required_cells = [[0, 0], [0, 1], [1, 0], [1, 1]]
    rnp.pos_start_addr = 0xa3d1
    rp.room_npc_placements.append(rnp)
    
    room_placements.append(rp)

    params.room_placements = room_placements
    
    RandomlyGenerateMultiRoomDungeonMap(params, filebytes)
    
    exit_pos = GetExitPosition(filebytes, clone_exits[0])
    SetExitPosition(filebytes, clone_exits[1], exit_pos[0], exit_pos[1])
    # clone exit pos for WoR (Final)
    exit_pos = GetExitPosition(filebytes, 0x08c)
    SetExitPosition(filebytes, 0x167, exit_pos[0], exit_pos[1])
    
    # Read back exit positions and return exit data in "room" format for exit connection randomization
    exits = [GetExitPosition(filebytes, entrance[1]) for entrance in entrances]
    room_format_data = []
    for i in range(0, len(entrances)):
        room_format_data.append([entrances[i][2], room_id, exits[i][0], exits[i][1]])
    return room_format_data
    
def RandomlyGenerateFourthTowerSection(filebytes):
    # Randomly generate tower rooms
    room17f = RandomlyGenerateTower17FMap(filebytes)
    room18f = RandomlyGenerateTower18FMap(filebytes)
    room19f = RandomlyGenerateTower19FMap(filebytes)
    room20f = RandomlyGenerateTower20FMap(filebytes)
    room21f = RandomlyGenerateTower21FMap(filebytes)
    
    # Randomize connections between tower rooms
    floor_16_pos = GetExitPosition(filebytes, 0x0d8)
    first_room = [[0x076, 0x10, floor_16_pos[0], floor_16_pos[1]]]
    # These rooms include the connection between the flower world on 21f and the hut,
    # so you might have to go through the hut to continue up the tower!
    remaining_rooms = [room17f, room18f, room19f, room20f, room21f, \
        [[0x08a, 0x16, 0x07, 0x08]], \
        [[0x0d8, 0x3f, 0x33, 0x14], [0x0d9, 0x3f, 0x33, 0x0d]], \
        [[0x0da, 0x40, 0x33, 0x14], [0x0db, 0x40, 0x33, 0x0d]], \
        [[0x0dc, 0x41, 0x33, 0x14], [0x0dd, 0x41, 0x33, 0x0d]], \
        [[0x0de, 0x42, 0x33, 0x14], [0x0df, 0x42, 0x33, 0x0d]], \
        [[0x0e0, 0x43, 0x33, 0x14], [0x0e1, 0x43, 0x33, 0x0d]], \
        [[0x0e2, 0x44, 0x33, 0x14], [0x0e3, 0x44, 0x33, 0x0d]], \
        [[0x0f0, 0x51, 0x0f, 0x0f]], \
        [[0x0f1, 0x52, 0x0b, 0x0a]], \
        [[0x0f3, 0x53, 0x07, 0x0d]], \
        [[0x0f4, 0x54, 0x10, 0x17], [0x0f5, 0x54, 0x21, 0x0c]], \
        [[0x0f9, 0x57, 0x22, 0x26]] \
        ]
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)

    return
    
def RandomlyGenerateTower17FMap(filebytes):
    entrances = [[0x0c, 0x0d9, 0x07c], [0x0a, 0x0da, 0x07b]]
    clone_exits = [0x0d9, 0x010]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe2d8, 150, 0x11, entrances, clone_exits)

def RandomlyGenerateTower18FMap(filebytes):
    entrances = [[0x0c, 0x0db, 0x07e], [0x0a, 0x0dc, 0x07d], [0x0e, 0x0f0, 0x07f]]
    clone_exits = [0x0db, 0x011]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe36e, 116, 0x12, entrances, clone_exits)

def RandomlyGenerateTower19FMap(filebytes):
    entrances = [[0x0c, 0x0dd, 0x081], [0x0a, 0x0de, 0x080], [0x0e, 0x0f1, 0x082]]
    clone_exits = [0x0dd, 0x012]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe3e2, 131, 0x13, entrances, clone_exits)

def RandomlyGenerateTower20FMap(filebytes):
    entrances = [[0x0c, 0x0df, 0x84], [0x0a, 0x0e0, 0x083], [0x0e, 0x0f3, 0x085]]
    clone_exits = [0x0df, 0x013]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe465, 106, 0x14, entrances, clone_exits)

def RandomlyGenerateTower21FMap(filebytes):
    entrances = [[0x0c, 0x0e1, 0x087], [0x0a, 0x0e2, 0x086], [0x0e, 0x0f5, 0x088]]
    clone_exits = [0x0e1, 0x014]
    return RandomlyGenerateTowerRoomMap(filebytes, 0xe4cf, 114, 0x15, entrances, clone_exits)

def ApplyIPSPatch(filebytes, patchbytes):
    patch_offset = 0
    patch_str = ""
    for i in range(0, 5):
        patch_str += chr(patchbytes[i])
    if not patch_str == "PATCH":
        return False
    patch_offset += 5
    while patch_offset < (len(patchbytes) - 5):
        chunk_offset = patchbytes[patch_offset + 2] + (patchbytes[patch_offset + 1] << 8) + (patchbytes[patch_offset] << 16)
        # print(hex(chunk_offset))
        patch_offset += 3
        chunk_size = patchbytes[patch_offset + 1] + (patchbytes[patch_offset] << 8)
        patch_offset += 2        
        
        if chunk_size == 0:
            # RLE chunk (repeated value)
            rle_size = patchbytes[patch_offset + 1] + (patchbytes[patch_offset] << 8)
            patch_offset += 2        
            rle_val = patchbytes[patch_offset]
            patch_offset += 1
            for i in range(0, rle_size):
                filebytes[chunk_offset + i] = rle_val
        else:
            # Regular chunk
            for i in range(0, chunk_size):
                if (chunk_offset + i) >= len(filebytes):
                    print("offset out of range:", hex(chunk_offset + i))
                    return False
                filebytes[chunk_offset + i] = patchbytes[patch_offset]
                # print(hex(patchbytes[patch_offset]))
                patch_offset += 1
    if patch_offset != (len(patchbytes) - 3):
        return False
    patch_str = ""
    for i in range(0, 3):
        patch_str += chr(patchbytes[patch_offset + i])
    if not patch_str == "EOF":
        return False
    
    return True
    
def FFLRandomize(seed, rompath, monstercsvpath, ffl2rompath, options, options_numbers):

    print("Seed: ", seed)
    random.seed(seed)
    
    print("Options:")
    for option in options.keys():
        if options[option] != default_options[option]:
            print(command_line_switches[option])
    for option in options_numbers.keys():
        print(command_line_switches_numbers[option], options_numbers[option])

    # read bytes from input file
    inf = open(rompath, 'rb')
    filebytes = bytearray(inf.read())
    inf.close()
    
    if options[PATCH]:
        print("Patching...")
        # read bytes from IPS patch file
        q = pathlib.Path(rompath).with_name("ffltrt16.ips")
        ipsf = open(q, "rb")
        ipsfilebytes = bytearray(ipsf.read())
        ipsf.close()
    
        # apply patch
        success = ApplyIPSPatch(filebytes, ipsfilebytes)
        if not success:
            raise Exception("Failed to apply IPS patch. It should be in the same directory as the rom, named \"ffltrt16.ips\"")
            
    # read FFL2 ROM
    ffl2bytes = []
    try:
        inf = open(ffl2rompath, 'rb')
        ffl2bytes = bytearray(inf.read())
        inf.close()
    except FileNotFoundError:
        pass

    ##########################

    # TESTS/HACKS

    # ExportMeatMonstersCSV(filebytes, rompath)
    # ExportItemsCSV(filebytes, rompath)
    
    # target_rooms = [0x11, 0x12, 0x13, 0x14, 0x15, 0x16]
    # for target_room in target_rooms:
        # print("EXITS LEADING TO", hex(target_room))
        # for exit_offset in range(0, 0x1da):
            # if filebytes[0x92d0 + (exit_offset * 3)] == target_room:
                # print(hex(exit_offset))
    
    ##########################

    print("Randomizing...")
    RandomizeFFLRomBytes(filebytes, monstercsvpath, ffl2bytes, seed, options, options_numbers)
    
    # construct output filename
    q = pathlib.Path(rompath).with_name("FFL_" + str(seed) + ".gb")
    print("Writing:", q)

    WriteBytesToFile(filebytes, q)
    
    return
    
def WriteBytesToFile(filebytes, filename):
    outf = open(filename, 'wb')
    outf.write(bytes(filebytes))
    outf.close()
    return
    
def PromptForOptions(options, options_numbers):

    prompt_strings = { MUTANT_ABILITIES:"Randomize mutant abilities?", \
        ARMOR:"Randomize armor?", COMBAT_ITEMS:"Randomize combat items?", \
        CHARACTER_ITEMS:"Randomize character items?", ENEMY_ITEMS:"Randomize enemy items?", \
        SHOPS:"Randomize shops?", CHESTS:"Randomize chests?", MONSTERS:"Randomize monsters?", \
        ENCOUNTERS:"Randomize encounters?", GUILD_MONSTERS:"Randomize guild monsters?", \
        HP_TABLE:"Randomize HP table?", MUTANT_RACE:"Randomize mutant race?", \
        MEAT:"Randomize meat transformations?", PATCH:"Apply patch before randomization?", \
        TOWER:"Randomize tower exits?", DUNGEONS:"Randomize dungeon exits?", SKYSCRAPER:"Randomize skyscraper exits?", \
        SMALL_PICS:"Randomize small pics?", WORLD_MAPS:"Randomize world maps?", \
        DUNGEON_MAPS:"Randomize dungeon maps?", TOWER_MAPS:"Randomize tower maps?" }
        
    number_prompt_strings = { TRANSFORMATION_LEVEL_ADJUST:"Edit meat transformation level adjust? Type number to edit:", \
        ENCOUNTER_LEVEL_ADJUST:"Edit encounter level adjust? Type number to edit:", \
        MONSTER_GOLD_OFFSET_ADJUST:"Edit monster gold table adjust? Type number to edit:", \
        GOLD_TABLE_AMOUNT_MULTIPLIER:"Edit gold table value multiplier? Type number to edit:" \
        }
        
    for switch in prompt_strings.keys():
        if options[switch]:
            response = input(prompt_strings[switch] + " Default Yes, type N for No:")
            if response.upper() == "N":
                options[switch]=False
        else:
            response = input(prompt_strings[switch] + " Default No, type Y for Yes:")
            if response.upper() == "Y":
                options[switch]=True
            
    for switch in number_prompt_strings.keys():
        response = input(number_prompt_strings[switch])
        try:
            options_numbers[switch] = float(response)
        except ValueError:
            pass
            
    return
    
def ApplyHarderEncounters(options_numbers):
    options_numbers[TRANSFORMATION_LEVEL_ADJUST] = -1
    options_numbers[ENCOUNTER_LEVEL_ADJUST] = 1
    options_numbers[MONSTER_GOLD_OFFSET_ADJUST] = -1
    options_numbers[GOLD_TABLE_AMOUNT_MULTIPLIER] = 0.7
    return
    
print("FFL Randomizer version", VERSION)

rompath = ""
ffl2rompath = ""
monstercsvpath = ""
seed = 0

default_options = { MUTANT_ABILITIES:True, ARMOR:True, COMBAT_ITEMS:True, CHARACTER_ITEMS:True, ENEMY_ITEMS:True, \
    SHOPS:True, CHESTS:True, MONSTERS:True, ENCOUNTERS:True, GUILD_MONSTERS:True, HP_TABLE:True,
    MUTANT_RACE:True, MEAT:True, PATCH:True, TOWER:True, DUNGEONS:True, SKYSCRAPER:True, SMALL_PICS:True,
    WORLD_MAPS:False, DUNGEON_MAPS:False, TOWER_MAPS:False }
    
options_numbers = { TRANSFORMATION_LEVEL_ADJUST:0, ENCOUNTER_LEVEL_ADJUST:0, MONSTER_GOLD_OFFSET_ADJUST:0, \
    GOLD_TABLE_AMOUNT_MULTIPLIER:1.0}
    
command_line_switches = { MUTANT_ABILITIES:"nomutantabilities", ARMOR:"noarmor", COMBAT_ITEMS:"nocombatitems", \
    CHARACTER_ITEMS:"nocharacteritems", ENEMY_ITEMS:"noenemyitems", \
    SHOPS:"noshops", CHESTS:"nochests", MONSTERS:"nomonsters", ENCOUNTERS:"noencounters", \
    GUILD_MONSTERS:"noguildmonsters", HP_TABLE:"nohptable", MUTANT_RACE:"nomutantrace", \
    MEAT:"nomeat", PATCH:"nopatch", TOWER:"notower", DUNGEONS:"nodungeons", SKYSCRAPER:"noskyscraper", \
    SMALL_PICS:"nosmallpics", WORLD_MAPS:"worldmaps", DUNGEON_MAPS:"dungeonmaps", TOWER_MAPS:"towermaps" }
    
command_line_switches_numbers = { TRANSFORMATION_LEVEL_ADJUST:"transformation_level", \
    ENCOUNTER_LEVEL_ADJUST:"encounter_level", MONSTER_GOLD_OFFSET_ADJUST:"monster_gold", \
    GOLD_TABLE_AMOUNT_MULTIPLIER:"gold_table_multiplier" \
    }
    
options = dict(default_options)

if len(sys.argv) >= 4:
    
    # Command line mode
    
    rompath = sys.argv[1]
    monstercsvpath = sys.argv[2]
    seed = int(sys.argv[3])
    switch_keys = list(command_line_switches.keys())
    switch_vals = list(command_line_switches.values())
    for argidx in range(4, len(sys.argv)):
        if sys.argv[argidx] in switch_vals:
            switchidx = switch_vals.index(sys.argv[argidx])
            option = switch_keys[switchidx]
            options[option] = not options[option]
    
    switch_keys = list(command_line_switches_numbers.keys())
    for switch_key in switch_keys:
        switch_val = command_line_switches_numbers[switch_key]
        if switch_val in sys.argv[4:]:
            switchidx = sys.argv.index(switch_val)
            if (switchidx + 1) < len(sys.argv):
                try:
                    options_numbers[switch_key] = float(sys.argv[switchidx + 1])
                except ValueError:
                    pass
                    
    if "harder_encounters" in sys.argv[4:]:
        ApplyHarderEncounters(options_numbers)
        
    if "ffl2" in sys.argv[4:]:
        ffl2idx = sys.argv.index("ffl2")
        if (ffl2idx + 1) < len(sys.argv):
            ffl2rompath = sys.argv[ffl2idx + 1]
    
else:

    # Interactive mode

    rompath = input("Enter rom filename including full path:")
    rompath = rompath.strip("\"")
    monstercsvpath = input("Enter monster CSV filename including full path:")
    monstercsvpath = monstercsvpath.strip("\"")
    ffl2rompath = input("Enter FFL2 rom filename including full path (optional):")
    ffl2rompath = ffl2rompath.strip("\"")
    seed_str = input("Enter seed, or leave blank for random:")
    seed = 0
    if len(seed_str) == 0:
        # construct random seed value using current time
        seed = int( time.time() * 1000.0 )
        seed = ((seed & 0xff000000) >> 24) + ((seed & 0x00ff0000) >> 8) + ((seed & 0x0000ff00) << 8) + ((seed & 0x000000ff) << 24)
    else:
        seed = int(seed_str)
    change_options = input("Change options? Default No, type Y for Yes:")
    if change_options.upper() == "Y":
        PromptForOptions(options, options_numbers)
    apply_harder_encounters = input("Make encounters harder? Default No, type Y for Yes:")
    if apply_harder_encounters:
        ApplyHarderEncounters(options_numbers)

FFLRandomize(seed, rompath, monstercsvpath, ffl2rompath, options, options_numbers)