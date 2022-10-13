# FFLRandomizer
Randomizer for Gameboy game The Final Fantasy Legend (1989).

Familiarity with the vanilla game is highly recommended.

Windows binary here: https://github.com/eclipseyy/FFLRandomizer/raw/main/randomize_ffl.zip

Written in Python 3.8 on Windows. I haven't tested other platforms. There isn't anything Windows-specific in there - pathlib is used for paths, etc - so it might work. Could have endianness issues. The Windows binary was created using pyinstaller.<br/>

## Running the randomizer

Copy the ips patch to the same directory as your FFL ROM. The patch is Tower Reversed's latest patch. It's automatically applied before randomization. I recommend letting this happen (which is the default) but you can disable it if you want.

You have to supply the path to the FFL rom and the path to the monster CSV. You can edit the monster CSV first if you want. You can optionally supply the seed value to use for the randomization. The randomizer generates one new rom file per run.

Silent mode: randomize_ffl rompath monstercsvpath seed \[options\]<br/>
You can specify multiple options, separated by spaces. Some combinations of options might unbalance the game.<br/>
For a tougher challenge, the harder_encounters option populates encounters with higher level monsters. Meat transformations and gold combat rewards are adjusted to compensate. harder_encounters is equivalent to transformation_level -1 encounter_level 1 monster_gold -1 gold_table_multiplier 0.7.<br/>
Gameplay should hopefully be reasonably balanced between seeds. Let me know if you find a very difficult or very easy seed. The difficulty might not be even within a particular randomized rom, but that's part of the fun; however, please let me know if you come across something ridiculous. Item costs should be fair; if you find items which seem very cheap or expensive, let me know.<br/>
If you want to cheat and see what's in a randomized rom, use Tower Reversed's fledermaus utility (link in Thanks section below).<br/>

| Switch                  | Meaning                                                                                           |
|-------------------------|---------------------------------------------------------------------------------------------------|
| nomutantabilities       | Disables randomization of mutant learnable abilities                                              |
| noarmor                 | Disables randomization of armor items                                                             |
| nocombatitems           | Disables randomization of combat items such as weapons and spells                                 |
| nocharacteritems        | Disables assigning appropriate items to guild humans and mutants                                  |
| noenemyitems            | Disables assigning appropriate items to enemies such as ASIGARU and KARATEKA                      |
| noshops                 | Disables randomizing equipment shop contents                                                      |
| nochests                | Disables randomizing chest contents                                                               |
| nomonsters              | Disables randomizing monsters by picking them from the CSV file                                   |
| noencounters            | Disables randomizing which monsters appear in encounters                                          |
| noguildmonsters         | Disables randomizing which monsters appear for selection in guilds                                |
| nohptable               | Disables randomizing the HP table used by monsters and guild characters                           |
| nomutantrace            | Disables randomizing the mutant race (see below)                                                  |
| nomeat                  | Disables randomizing meat transformation table                                                    |
| nopatch                 | Disables applying the patch (IPS file) before randomization                                       |
| notower                 | Disables randomizing connections between rooms in the tower                                       |
| nodungeons              | Disables randomizing connections between exits in certain dungeons and caves                      |
| noskyscraper            | Disables randomizing connections between exits in the skyscraper                                  |
| transformation_level x  | Sets the monster level offset for meat transformation randomization                               |
| encounter_level x       | Sets the monster level offset for encounter randomization                                         |
| monster_gold x          | Sets the gold table offset for combat rewards                                                     |
| gold_table_multiplier x | Sets multiplier for values in the gold table                                                      |
| harder_encounters       | equivalent to transformation_level -1 encounter_level 1 monster_gold -1 gold_table_multiplier 0.7 |
| nosmallpics             | Disables randomization of small pictures                                                          |
| ffl2 ffl2rompath        | Sets path to FFL2 ROM, currently used only for randomization of small pictures                    |
| nocontinent             | Disables randomization of the World of Continent map                                              |

When mutant race randomization is enabled (which is the default), MUTANT will be renamed to S-MUT, A-MUT or D-MUT depending on which attribute is learned most quickly.<br/>
When tower randomization is enabled (which is the default), you will likely visit the floors out of numerical order.

## Combat items

Randomized items have their properties encoded into their names.

RNC is RUNE type, DEF is DEFEND, RD is both RUNIC and DEFEND, and RVG counters. FSK, ISK, ESK and PSK grant "special body" with a single element, the same as BURNING or P-SKIN.

Armor example: (armor symbol)5ODMG - armor that gives 5 D points and resistance equivalent to ODAMAGE.
Numbers are the defense increase. OICE etc are resistances. S, A, M and SA are attribute increases.

Sword example: (sword symbol)A5RNC - agility-based weapon with power 5 and the ability to reflect magic.
S, M and A give the damage type: S for Strength (HAMMER, LONG, AXE etc); M for Mana (P-KNIFE, P-SWORD); A for Agility (RAPIER, SABER etc). The number is the weapon strength. CRL, OGR, DGN, SUN deal critical hits to single classes, CLS to all four classes. FLM, ICE, ELC deal elemental hits, KNG hits all elements.

Bow example: B100RVG - bow with 100 power and the ability to counter.

Gun example: (gun symbol)50RNC

Whip example: W45RVG

Ordnance example: O75RNC

Spells: (spellbook symbol)FIRA8 - fire-elemental spell with power 8 that targets all enemies<br/>
FIR, ICE, ELC, FOG, QUK and FRC target one enemy group. Each has a single element, except FRC, which has no element.<br/>
FIRA, TRND, ELCA, ACID, QUKA and FLAR target all enemies.<br/>

## Thanks

Infinite thanks: https://towerreversed.neocities.org/, the "fledermaus" utility in particular.

Contact: eclipseyy@gmx.com. PLEASE email me with your feedback, suggestions, etc! I haven't spent a lot of time playtesting it, so all feedback is super valuable.

## Version history

v0.011 - bug fix<br/>
v0.010 - randomize small pictures, optionally copying them from FFL2 ROM. Randomly generate the World of Continent map<br/>
v0.009 - prompt for harder encounters option in interactive mode<br/>
v0.008 - harder_encounters option. Tweak monster CSV a bit.<br/>
v0.007 - randomize dungeon and skyscraper exits<br/>
v0.006 - randomize connections between rooms in the tower. Tweaks, bug fixes.<br/>
v0.005 - options. Randomize shops and chests multiple times to find the lowest number of unused items in the game. Bug fixes, tweaks and improvements.<br/>
v0.004 - bug fix<br/>
v0.003 - randomization of other combat items. Bug fixes and balancing tweaks. Undid transforming into non-monster enemies as in practice it's usually unwanted.<br/>
v0.002 - added armor and melee weapon randomization. Greatly improved meat transformation (thanks Tower Reversed). Monsters eating meat now sometimes transform into non-monsters! Automatically apply TR Tweaks patch. Many tweaks.<br/>
v0.001 - initial<br/>
