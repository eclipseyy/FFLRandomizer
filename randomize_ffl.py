import random
import time
import pathlib
import csv
import sys

VERSION = "0.001"

def RandomizeFFLRomBytes(filebytes, monstercsvpath):

    # OBSOLETE_RandomizeItemAttributes(filebytes)
    RandomizeMutantAbilityLearnList(filebytes)

    RandomizeEquipmentShops(filebytes)
    RandomizeChests(filebytes)

    encounter_meat_levels = ReadAllEncounterCharacterMeatLevels(filebytes)

    RandomizeMonsters(filebytes, monstercsvpath)

    for encounter_id in range(0, 0x80):
        RandomizeEncounterMonstersByMeatLevel(filebytes, encounter_id, encounter_meat_levels[encounter_id])

    RandomizeGuildMonsters(filebytes)
    RandomizeHPTable(filebytes)
    ReplaceMutantRace(filebytes)
    RandomizeMeatTransformationTable(filebytes)

    return

def OBSOLETE_RandomizeItemAttributes(filebytes):

    # Randomize x and y attributes of selected items to between 50% and 150% of their original value

    item_ids_randomize_x_and_y = [0x00, 0x01, 0x02, 0x03, 0x0e, 0x0f, \
                                  0x10, 0x1b, \
                                  0x35, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, \
                                  0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, \
                                  0x72, 0x73, 0x74, 0x75, 0x76, 0x77]

    item_ids_randomize_x = [0x11, 0x12, \
                            0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, \
                            0x29, 0x2a, 0x2b, 0x2c, 0x2e, 0x2f, \
                            0x30, 0x31, 0x32, 0x34, 0x36, \
                            0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, \
                            0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, \
                            0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, \
                            0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e]

    item_ids_randomize_y = [0x0c, 0x0d, 0x13, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51]

    for item_id in range(0, 256):
        x_offset = 0x0001b704 + (8 * item_id)
        y_offset = 0x0001b705 + (8 * item_id)

        if (item_id in item_ids_randomize_x_and_y) or (item_id in item_ids_randomize_x):
            RandomizeByteWithinMultipliers(filebytes, x_offset, 0.5, 1.5)
        if (item_id in item_ids_randomize_x_and_y) or (item_id in item_ids_randomize_y):
            RandomizeByteWithinMultipliers(filebytes, y_offset, 0.5, 1.5)

    return

def RandomizeMutantAbilityLearnList(filebytes):

    remaining_ability_ids = list(range(0x80, 0xfc))
    ability_ids = []
    while len(ability_ids) < 31:
        abil_pick = random.choice(remaining_ability_ids)
        abil_type = ReadItemType(filebytes, abil_pick)
        # Don't pick abilities of type Strike S (0x06) or Strike A (0x0b)
        if not (abil_type == 0x06) and not (abil_type == 0x0b):
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

    # There are 11 equipment shops. Each has ten slots, one byte each.
    # The first starts at 0x00017d38 and shops are spaced 0x14 apart
    # (the intervening bytes being item shops)

    for i in range(0, 11):

        min_cost = 999999
        max_cost = 0

        shop_start_idx = 0x00017d38 + (0x14 * i)

        # Need to be able to buy battle sword to advance the story.
        # For now, keep battle sword in any shops that contain it
        contains_battle_sword = False

        for j in range(0, 10):
            item = filebytes[shop_start_idx + j]
            if item < 0x80:
                item_cost = ReadItemCost(filebytes, item)
                min_cost = min(min_cost, item_cost)
                max_cost = max(max_cost, item_cost)
                if item == 0x23:
                    contains_battle_sword = True

        max_cost = int(max_cost * 1.2)
        
        new_shop_items = []

        if contains_battle_sword:
            new_shop_items.append(0x23)
            
        while len(new_shop_items) < 10:
            # eligible items for shops are 0x02, 0x1b, and 0x20-0x79 inclusive
            pick = random.randrange(0x20, 0x7c)
            if pick == 0x7a:
                pick = 0x02
            if pick == 0x7b:
                pick = 0x1b

            if pick in new_shop_items:
                continue

            item_cost = ReadGPCost(filebytes, 0x00017e10 + (3 * pick))

            if (item_cost > 0) and (item_cost <= max_cost) and (item_cost >= min_cost):
                new_shop_items.append(pick)

        # sort new shop items by GP cost
        new_shop_items.sort(key = lambda x: ReadItemCost(filebytes, x))

        for j in range(0, len(new_shop_items)):
            filebytes[shop_start_idx + j] = new_shop_items[j]

    return

def RandomizeMonsters(filebytes, monstercsvpath):
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

        success = WriteMonstersToGame(filebytes, game_monsters)

    return

def WriteMonstersToGame(filebytes, game_monsters):

    success = True

    # Check the total number of abilities is <= 991 (the maximum)
    abils = ReadAllCharacterAbilities(filebytes)
    ParseMonsterAbilitiesIntoCharacterAbilities(abils, game_monsters)
    total_num_abils = sum([len(i) for i in abils])
    if total_num_abils > 991:
        success = False

    if success:
        WriteAllCharacterAbilities(filebytes, abils)

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
    filebytes[startidx + 1] = byte

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
    return (filebytes[0x0001b707 + (item_id * 8)] & 0x2e)

def WriteItemSFX(filebytes, item_id, val):
    filebytes[0x0001b707 + (item_id * 8)] |= (val & 0x2e)
    return

def ReadItemFieldEffectA(filebytes, item_id):
    return filebytes[0x00003739 + (item_id * 2)]

def WriteItemFieldEffectA(filebytes, item_id, val):
    filebytes[0x00003739 + (item_id * 2)] = val
    return

def ReadItemFieldEffectB(filebytes, item_id):
    return filebytes[0x0000373a + (item_id * 2)]

def WriteItemFieldEffectB(filebytes, item_id, val):
    filebytes[0x0000373a + (item_id * 2)] = val
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
    allencountermeatlevels = []
    for encidx in range(0, 0x80):
        encountermeatlevels = []
        for charidx in range(0, 3):
            char = ReadEncounterCharacter(filebytes, encidx, charidx)
            encountermeatlevels.append(ReadMeatLevel(filebytes, char))
        allencountermeatlevels.append(encountermeatlevels)
    return allencountermeatlevels

# Picks random monsters for the specified encounter which match the target meat levels
# Only replaces monsters (0x00-0x95). Does not replace non-monster enemies or bosses (> 0x96)
def RandomizeEncounterMonstersByMeatLevel(filebytes, encounter_idx, target_meat_levels):

    new_encounter_characters = []
    for charpos in range(0, 3):
        new_encounter_characters.append(ReadEncounterCharacter(filebytes, encounter_idx, charpos))

    for charpos in range(0, 3):
        if(ReadEncounterCharacter(filebytes, encounter_idx, charpos) < 0x96):
            target_meat_level = target_meat_levels[charpos]
            success = False
            while((not success) and (target_meat_level >= 0)):
                success = True
                # Starting from a random offset and wrapping around, take the first monster with a matching meat level
                # which doesn't already appear in the encounter
                random_offset = random.randrange(0, 0x95)
                for i in range(0, 0x96):
                    idx = (i + random_offset) % 0x96
                    if not idx in new_encounter_characters:
                        if(ReadMeatLevel(filebytes, idx) == target_meat_level):
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

def ReadItemName(filebytes, idx):
    name = ""
    for i in range(0, 7):
        name += chr(FFLNameTextToASCII(filebytes[0x00014640 + (idx * 8) + i]))
    return name

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
    # Randomize the meat table without many constraints.
    # The result will have more "nothing happened"s than FFL;
    # eating the meat of the same class as the eater may result in transformation;
    # some monsters might be unable to transform at all;
    # and many monsters may be impossible to get.
    # Hopefully the result is that monsters are much harder to exploit.
    for addr in range(0x0000afd3, 0x0000b2a8):
        pick = random.randrange(0, 0x80)
        if pick > 0x18: # 0x18 is the last valid value
            pick = 0xff # 0xff is "nothing happened"
        filebytes[addr] = pick

def RandomizeChests(filebytes):
    # Pick a random item for each chest (except chests with story items)
    # which is between 75% and 125% of the value of the original item
    addrs = [0xa404, 0xa429, 0xa44e, 0xa47c, 0xa4bf, 0xa4c8, 0xa4d1, 0xa4da, 0xa4e3, 0xa4ec, 0xa4f3, \
             0xa4fa, 0xa501, 0xa513, 0xa53b, 0xa544, 0xa5d7, 0xa5de, 0xa5e5, 0xa8c0, 0xa8c7, 0xa8ce, \
             0xa9f4, 0xa9fb, 0xaa02, 0xab0f, 0xab16, 0xab1d, 0xab24, 0xab2b, 0xab32, 0xae1d, 0xae26, \
             0xae2f, 0xae38, 0xaf59, 0xaf62, 0xaf6b, 0xa51c, 0xa50a]
    item_values = [30000, 10000, 200000, 10000, 80, 800, 3800, 4000, 6000, 200, 15000, 10000, 32000, \
                   8000, 50000, 50000, 10000, 10000, 50, 50, 300, 40, 1000, 2500, 800, 200, 10000, \
                   15000, 5000, 5000, 10480, 5000, 200, 23200, 15000, 100000, 200, 10000, 8000, 5000]
    for i in range(0, len(addrs)):
        valid = False
        pick = 0xff
        while not valid:
            pick = random.randrange(0x80)
            # exclude story items
            valid = not pick in [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x1f, 0x7e, 0x7f]
            if valid:
                pick_cost = ReadItemCost(filebytes, pick)
                valid = ((pick_cost >= (item_values[i] * 0.75)) and (pick_cost <= (item_values[i] * 1.25)))
        addr = addrs[i]
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

def ExportItemsCSV(filebytes):

    p = pathlib.Path(INFILE).with_name("FFLItems.csv")

    f = open(p, mode='w')

    f.write("Name,Uses,Cost,FlagsA,FlagsB,Type,AltUses,X,Y,GFX,Group,SFX,UsedByChrs\n")

    for idx in range(0, 0x80):

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

        # UsedByChrs. Flag is true if the item is used by enemies
        used_by_chrs = False
        for chridx in range(0, 0xc8):
            if (chridx >= 0xad) and (chridx < 0xbd): # exclude guild HUMANs and MUTANTs
                continue
            abils = ReadCharacterAbilList(filebytes, chridx)
            if idx in abils:
                used_by_chrs = True
                break
        f.write(str(used_by_chrs))
        f.write(',')

        f.write('\n')

def FFLRandomize(seed, rompath, monstercsvpath):

    print("seed: ", seed)
    random.seed(seed)

    # read bytes from input file
    inf = open(rompath, 'rb')
    filebytes = bytearray(inf.read())
    inf.close()

    ##########################

    # TESTS/HACKS

    # ExportMeatMonstersCSV(filebytes, rompath)
    # ExportItemsCSV(filebytes)

    ##########################

    RandomizeFFLRomBytes(filebytes, monstercsvpath)

    # construct output filename
    q = pathlib.Path(rompath).with_name("FFL_" + str(seed) + ".gb")
    print("Writing:", q)

    # write bytes to output file
    outf = open(q, 'wb')
    outf.write(bytes(filebytes))
    outf.close()
    
    return

print("FFL Randomizer version", VERSION)

rompath = ""
monstercsvpath = ""
seed = 0

if len(sys.argv) == 4:
    rompath = sys.argv[1]
    monstercsvpath = sys.argv[2]
    seed = int(sys.argv[3])
else:
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

FFLRandomize(seed, rompath, monstercsvpath)
