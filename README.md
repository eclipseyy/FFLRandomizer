# FFLRandomizer
Randomizer for Gameboy game The Final Fantasy Legend (1989).

Windows binary here: https://github.com/eclipseyy/FFLRandomizer/raw/main/randomize_ffl.zip

Written in Python 3.8 on Windows. I haven't tested other platforms. There isn't anything Windows-specific in there - pathlib is used for paths, etc - so it might work. Could have endianness issues. The Windows binary was created using pyinstaller.

Copy the ips patch to the same directory as your FFL ROM.

You have to supply the path to the FFL rom and the path to the monster CSV. You can edit the monster CSV first if you want. You can optionally supply the seed value to use for the randomization. The randomizer generates one new rom file per run.

Silent mode: randomize_ffl rompath monstercsvpath seed

Currently randomized:
- monsters, picked from CSV file
- encounters
- meat transformations
- equipment shop contents
- chest contents
- mutant attribute learn rates and amounts (one of four choices)
- mutant learnable abilities
- armor
- melee weapons

Armor properties are encoded in the item names. Numbers are the defense increase. OICE, XDMG etc are resistances/weaknesses. S, A, M and SA are attribute increases.

Melee weapon names also give you the item properties. S, M and A give the damage type: S for Strength (HAMMER, LONG, AXE etc); M for Mana (P-KNIFE, P-SWORD); A for Agility (RAPIER, SABER etc). The number is the weapon strength. RNC is RUNE type, DEF is DEFEND, RD is both RUNIC and DEFEND, and RVG counters. CRL, OGR, DGN, SUN deal critical hits to single classes, CLS to all four classes. FLM, ICE, ELC deal elemental hits, KNG hits all elements.

Gameplay should hopefully be reasonably balanced between seeds. Let me know if you find a very difficult or very easy seed.

Future:
- switches to control which features are randomized
- randomize non-monster enemies
- randomize items
- investigate and improve meat transformation
- improve monster CSV
- etc

Infinite thanks: https://towerreversed.neocities.org/, the "fledermaus" utility in particular.

Contact: eclipseyy@gmx.com. PLEASE email me with your feedback, suggestions, etc! I haven't spent a lot of time playtesting it, so all feedback is super valuable.

Version history:

v0.002 - added armor and melee weapon randomization. Greatly improved meat transformation (thanks Tower Reversed). Monsters eating meat now sometimes transform into non-monsters! Automatically apply TR Tweaks patch. Many tweaks.

v0.001 - initial
