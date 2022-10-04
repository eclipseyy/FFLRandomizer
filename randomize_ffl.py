import random
import time
import pathlib
import csv
import sys

VERSION = "0.008"

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

def RandomizeFFLRomBytes(filebytes, monstercsvpath, seed, options, options_numbers):

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

def RandomizeTowerSection(filebytes, first_room, remaining_rooms):
    
    # Each room is a list of exits, and each exit is a list with four data members, defined as follows:
    # [0] is exit offset
    # [1] is room ID for return
    # [2] is X coordinate for return
    # [3] is Y coordinate for return
    
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
        
    RandomizeTowerSection(filebytes, first_room, remaining_rooms)
        
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
    
def FFLRandomize(seed, rompath, monstercsvpath, options, options_numbers):

    print("Seed: ", seed)
    random.seed(seed)
    
    print("Options:")
    for option in options.keys():
        if not options[option]:
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

    ##########################

    # TESTS/HACKS

    # ExportMeatMonstersCSV(filebytes, rompath)
    # ExportItemsCSV(filebytes, rompath)
    
    ##########################

    print("Randomizing...")
    RandomizeFFLRomBytes(filebytes, monstercsvpath, seed, options, options_numbers)
    
    # construct output filename
    q = pathlib.Path(rompath).with_name("FFL_" + str(seed) + ".gb")
    print("Writing:", q)

    # write bytes to output file
    outf = open(q, 'wb')
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
        TOWER:"Randomize tower exits?", DUNGEONS:"Randomize dungeon exits?", SKYSCRAPER:"Randomize skyscraper exits?" \
        }
        
    number_prompt_strings = { TRANSFORMATION_LEVEL_ADJUST:"Edit meat transformation level adjust? Type number to edit:", \
        ENCOUNTER_LEVEL_ADJUST:"Edit encounter level adjust? Type number to edit:", \
        MONSTER_GOLD_OFFSET_ADJUST:"Edit monster gold table adjust? Type number to edit:", \
        GOLD_TABLE_AMOUNT_MULTIPLIER:"Edit gold table value multiplier? Type number to edit:" \
        }
        
    for switch in prompt_strings.keys():
        options[switch]=True
        response = input(prompt_strings[switch] + " Default Yes, type N for No:")
        if response == "N":
            options[switch]=False
            
    for switch in number_prompt_strings.keys():
        response = input(number_prompt_strings[switch])
        try:
            options_numbers[switch] = float(response)
        except ValueError:
            pass
            
    return
    
print("FFL Randomizer version", VERSION)

rompath = ""
monstercsvpath = ""
seed = 0

options = { MUTANT_ABILITIES:True, ARMOR:True, COMBAT_ITEMS:True, CHARACTER_ITEMS:True, ENEMY_ITEMS:True, \
    SHOPS:True, CHESTS:True, MONSTERS:True, ENCOUNTERS:True, GUILD_MONSTERS:True, HP_TABLE:True,
    MUTANT_RACE:True, MEAT:True, PATCH:True, TOWER:True, DUNGEONS:True, SKYSCRAPER:True }
    
options_numbers = { TRANSFORMATION_LEVEL_ADJUST:0, ENCOUNTER_LEVEL_ADJUST:0, MONSTER_GOLD_OFFSET_ADJUST:0, \
    GOLD_TABLE_AMOUNT_MULTIPLIER:1.0}
    
command_line_switches = { MUTANT_ABILITIES:"nomutantabilities", ARMOR:"noarmor", COMBAT_ITEMS:"nocombatitems", \
    CHARACTER_ITEMS:"nocharacteritems", ENEMY_ITEMS:"noenemyitems", \
    SHOPS:"noshops", CHESTS:"nochests", MONSTERS:"nomonsters", ENCOUNTERS:"noencounters", \
    GUILD_MONSTERS:"noguildmonsters", HP_TABLE:"nohptable", MUTANT_RACE:"nomutantrace", \
    MEAT:"nomeat", PATCH:"nopatch", TOWER:"notower", DUNGEONS:"nodungeons", SKYSCRAPER:"noskyscraper" }
    
command_line_switches_numbers = { TRANSFORMATION_LEVEL_ADJUST:"transformation_level", \
    ENCOUNTER_LEVEL_ADJUST:"encounter_level", MONSTER_GOLD_OFFSET_ADJUST:"monster_gold", \
    GOLD_TABLE_AMOUNT_MULTIPLIER:"gold_table_multiplier" \
    }

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
            options[option] = False
    
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
        options_numbers[TRANSFORMATION_LEVEL_ADJUST] = -1
        options_numbers[ENCOUNTER_LEVEL_ADJUST] = 1
        options_numbers[MONSTER_GOLD_OFFSET_ADJUST] = -1
        options_numbers[GOLD_TABLE_AMOUNT_MULTIPLIER] = 0.7
        
else:

    # Interactive mode

    rompath = input("Enter path to rom:")
    rompath = rompath.strip("\"")
    monstercsvpath = input("Enter path to monster CSV:")
    monstercsvpath = monstercsvpath.strip("\"")
    seed_str = input("Enter seed, or leave blank for random:")
    seed = 0
    if len(seed_str) == 0:
        # construct random seed value using current time
        seed = int( time.time() * 1000.0 )
        seed = ((seed & 0xff000000) >> 24) + ((seed & 0x00ff0000) >> 8) + ((seed & 0x0000ff00) << 8) + ((seed & 0x000000ff) << 24)
    else:
        seed = int(seed_str)
    change_options = input("Change options? Default No, type Y for Yes:")
    if change_options == "Y":
        PromptForOptions(options, options_numbers)

FFLRandomize(seed, rompath, monstercsvpath, options, options_numbers)
