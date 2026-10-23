# Image regeneration

- `list.json`: events whose images need regenerating. `wrong_batch1` are first-batch images that came out wrong; `npc_major` are events with a major non-player character; `all_to_regenerate` is the union (379). `npc_roster` counts events per NPC.
- `portraits.json`: every character named in `list.json` mapped to one portrait file. Lirael, Brand and Sazed use the portraits in `gen/refs/`, with their Roll20 art noted as `roll20_file`. Everyone else uses their Roll20 character art from `gen/refs/roll20/`. Glade Amberwood has no portrait.
- `sources.json`: built from the two files above. Each event to regenerate with the portrait files of the characters in it. Player characters are added when their name appears in the event text, the same way `gen/image.py` picks them.

Rebuild `sources.json` after editing either input:

    python3 -I gen/regen/build_sources.py

It stops with a list of problems if a character has no entry in `portraits.json` or a mapped file does not exist.
