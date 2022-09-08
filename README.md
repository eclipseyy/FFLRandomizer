# FFLRandomizer
Randomizer for Gameboy game The Final Fantasy Legend (1989).

Windows binary here: https://github.com/eclipseyy/FFLRandomizer/releases/download/v0.001/randomize_ffl.zip

Written in Python 3.8 on Windows. I haven't tested other platforms, but I don't think there's anything Windows-specific in there - pathlib is used for paths, etc - so it might work.

Currently randomized:
- monsters, picked from CSV file
- encounters
- meat transformations
- shop contents
- chest contents
- mutant attribute learn rates and amounts (one of four choices)
- mutant learnable abilities

You have to supply the path to the FFL rom and the path to the monster CSV. You can edit the monster CSV first if you want. You can optionally supply the seed value to use for the randomization. The randomizer generates one new rom file per run.

I tried to balance game difficulty to be fairly similar to vanilla FFL. The biggest difference is in monster meat eating. There's a much higher chance of transforming into a higher level monster when eating meat, compared to vanilla FFL. To compensate for this, there's a much higher chance of "nothing happened" when eating meat. Meat transformation is randomized quite crudely; eating the meat of your own monster type might cause a transformation, and in some seeds, there might be some monsters who cannot transform at all.

Future:
- switches to control which features are randomized
- randomize non-monster enemies
- randomize items
- investigate and improve meat transformation
- improve monster CSV
- etc

Infinite thanks: https://towerreversed.neocities.org/, the "fledermaus" utility in particular.

Version history:

v0.001 - initial
