# FFLRandomizer
Randomizer for Gameboy game The Final Fantasy Legend (1989).

Windows binary here: https://github.com/eclipseyy/FFLRandomizer/raw/main/randomize_ffl.zip

Written in Python 3.8 on Windows. I haven't tested other platforms. There isn't anything Windows-specific in there - pathlib is used for paths, etc - so it might work. Could have endianness issues. The Windows binary was created using pyinstaller.

Copy the ips patch to the same directory as your FFL ROM. The patch is Tower Reversed's latest patch. It's automatically applied before randomization. I recommend letting this happen (which is the default) but you can disable it if you want.

You have to supply the path to the FFL rom and the path to the monster CSV. You can edit the monster CSV first if you want. You can optionally supply the seed value to use for the randomization. The randomizer generates one new rom file per run.

Silent mode: randomize_ffl rompath monstercsvpath seed \[options\]<br/>
Valid options are "nomutantabilities", "noarmor", "nocombatitems", "nocharacteritems", "noenemyitems", "noshops", "nochests", "nomonsters", "noencounters", "noguildmonsters", "nohptable", "nomutantrace", "nomeat", "nopatch", "notower", "nodungeons", "noskyscraper". You can specify multiple options, separated by spaces.<br/>
Some combinations of options might unbalance the game. For example, if you use "noencounters" without "nomonsters", some encounters will probably have inappropriately high level monsters, and be difficult to win.

Currently randomized:
- monsters, picked from CSV file
- encounters
- meat transformations
- equipment shop contents
- chest contents
- mutant attribute learn rates and amounts (one of four choices - MUTANT will be renamed to S-MUT, A-MUT or D-MUT depending on which attribute is learned most quickly)
- mutant learnable abilities
- armor
- combat items
- connections between rooms in the tower
- connections between exits in some dungeons
- connections between rooms in the skyscraper

Gameplay should hopefully be reasonably balanced between seeds. Let me know if you find a very difficult or very easy seed. The difficulty might not be even within a particular randomized rom, but that's part of the fun. Item costs should be fair. If you find items which seem very cheap or expensive, let me know.

If you want to cheat and see what's in a randomized rom, use Tower Reversed's fledermaus utility.

Future:
- randomize connections between rooms in other places
- randomize non-monster enemies?
- improve monster CSV
- etc

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

v0.007 - randomize dungeon and skyscraper exits<br/>
v0.006 - randomize connections between rooms in the tower. Tweaks, bug fixes.<br/>
v0.005 - options. Randomize shops and chests multiple times to find the lowest number of unused items in the game. Bug fixes, tweaks and improvements.<br/>
v0.004 - bug fix<br/>
v0.003 - randomization of other combat items. Bug fixes and balancing tweaks. Undid transforming into non-monster enemies as in practice it's usually unwanted.<br/>
v0.002 - added armor and melee weapon randomization. Greatly improved meat transformation (thanks Tower Reversed). Monsters eating meat now sometimes transform into non-monsters! Automatically apply TR Tweaks patch. Many tweaks.<br/>
v0.001 - initial<br/>
