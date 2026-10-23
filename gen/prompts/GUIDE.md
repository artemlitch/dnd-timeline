# Writing an event's image prompt

One file per event: `gen/prompts/<event-id>.prompt.txt`. `gen/image.py` fills the `{...}` placeholders from
shared files, so a prompt only carries what is specific to its moment. The eight files already in this folder are
worked examples; `immovable-rod-and-elwood.prompt.txt` and `the-fury-ritual.prompt.txt` are the best ones to copy.

## Template

```
{tone}
This scene is <one plain line on what kind of scene it is: a street fight, a quiet conversation, an ambush...>.

FRAMING
{framing:<epic|wide|medium|close>}

SETTING
{setting:<setting-id>/<sublocation-id>}
In this moment: <only what this event changed or placed there: fire, bodies, a parked ship, a crowd>. Time and light: <from the recap>.
{maps:<Roll20 page name>}

THE MOMENT
<the single moment to draw>

CAST
- {cast:<Name>}
- <Name>: <one-line description, only for characters with no portrait>

REFERENCES
{references}
```

## Sources

- `site/timeline.json`: the event (title, summary, detail, session, date).
- `gen/world/campaign.txt`: the full session recap. Find the event's session header ("Session 24:") and read the
  whole passage around the event, not just the event text. This is the main source; never invent plot.
- `gen/world/settings.json`: settings and sub-locations. Pick the one the event happens in; `{setting:id}` alone
  if no sub-location fits. The landscape, terrain, plants, buildings and climate of a place come ONLY from its
  setting (and maps); a prompt never describes them. If no setting fits, report it rather than describing the place.
- `gen/world/setting_maps.json` (+ `gen/refs/roll20/maps/index.json`): Roll20 maps per setting/sub-location. Attach
  one map (two at most) that shows this place: `{maps:Page Name}`, or `{maps:Page Name#2}` for a page's second
  image. Look at the thumbnail in `gen/refs/roll20/maps/thumbs/` first; skip maps that are a different place or an
  empty battle grid. No fitting map: leave the line out.
- `gen/regen/sources.json`: the event's `refs`, the portraits that get attached, in order.
- `gen/world/framing.json`: `epic` for town-wide battles and huge events, `wide` for fights and group scenes,
  `medium` for most conversations and smaller action, `close` for intimate or emotional beats.

## Rules

1. **One moment.** Pick the single most dramatic or telling instant of the event and describe it concretely: who
   is where, doing what, facing whom, holding what.
2. **Put every visual oddity from the recap in, prominently.** The campaign is full of absurd things (lingerie-clad
   dancing dwarves, a frog-man swallowing people, birds in love with mercenaries). They must be in the image,
   described literally. Never label a scene as comedy, slapstick, absurd or funny: the shared tone already says
   comedy is played straight with a serious tone.
3. **Never tone down violence.** Gore, wounds, corpses and mutilation go in as the recap says, visceral and bloody.
   The shared tone tells the model how to handle what it cannot show.
4. **Nudity that is part of the story is represented, never explicit**: say the person is unclothed and let
   framing, bindings, shadow, smoke or cloth cover them. Always state that such a person is an adult.
5. **No style, lighting, atmosphere, landscape or climate in the prompt** (no "moody", "cinematic", colour palettes,
   smoke for effect, no forests, hills, trees, mountains, weather or vegetation). The style lives in the shared
   tone; the look of a place comes only from its setting and maps. "In this moment" holds only what the event
   itself changed or placed there. The only light you add is "Time and light:" from the recap: time of day, fire,
   lamps actually there.
6. **Cast.** Every name in the event's `refs` gets `- {cast:<Name>}` with the name spelled exactly as in
   sources.json. Characters who appear but have no portrait get a one-line description (species, build, hair,
   clothes) from the recap. If a portrait character is in `refs` but not present at the chosen moment, write
   `- <Name>'s portrait is attached for reference only; <Name> is not in this moment. Do not draw them.`
7. **Scene-specific outfits.** A {cast:Name} line and the character outline both show the usual outfit. When the
   moment changes it (unclothed, disguised, prison fatigues), replace that character's {cast:} line with a hand-written
   line that describes them without the usual outfit and says so explicitly.
8. **No colour idioms.** The model draws them literally: "red-faced" gave Paxon a solid red face. Write "flushed
   cheeks", "pale with shock" only for characters whose skin allows it, or describe the expression instead.
9. **No text in the scene.** Do not describe signs, banners, books or posters with readable words.
10. **Check your file** with the free dry run, which prints the finished prompt and calls no API:
   `python3 -I gen/image.py <event-id> --print`
   Never run gen/image.py without `--print`: every real run costs money.
