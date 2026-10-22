# Ravenwick Manor: illustrated working-memory floor plan

Copy **both** `world_view.py` and the complete `assets/` directory into `src/reasoning/` in your existing project. Keep the images beside the module in `src/reasoning/assets/`. Restart the notebook kernel after replacing the earlier module. This is display code, separate from the generic engine and domain knowledge. No drawing packages, network access or image assets are needed. Jupyter's existing IPython display support is used only by `show()`.

```python
from reasoning.engine import WorkingMemory
from reasoning.domains import TASK2_INITIAL_FACTS  # Adjust your domain import.
from reasoning.world_view import WorldView

wm = WorkingMemory(TASK2_INITIAL_FACTS)
view = WorldView(TASK2_INITIAL_FACTS, actor="sherlock", target="foyer")
view.show(wm, 0)
```

After your own engine executes an action:

```python
# Use your existing action-selection and step code here.
view.show(wm, 1)
```

For a single picture updated in place:

```python
view.show(wm, 0, replace=True)
# Execute an action with your engine, then:
view.show(wm, 1, replace=True)
```

`view.render(wm, t)` returns an object that also displays when it is the final expression in a notebook cell. `view.render(wm, t).save("state_1.svg")` optionally exports a snapshot. `view.inspect(wm, t)` returns the parsed display model for debugging. Methods accept either WorkingMemory (with `.facts`) or an iterable of fact tuples. They do not mutate it, advance time, choose actions or prove anything.

## Facts understood

- `("location", room, t)`
- `("at", entity, room, t)`
- `("object", object_name, t)`
- `("evidence", object_name, t)`
- `("empty", actor, t)`
- `("holding", object_name, t)` — one-actor world
- `("holding", actor, object_name, t)` — actor-explicit alternative
- `("passage", from_room, to_room, t)` — directed

Use the holding format your engine already produces; do not add an object location solely to make it display while held. A held object's map position comes from the robot. A fact at time 0 does not establish a location at time 1.

The initial facts provide a persistent *display roster* of objects/evidence and reference passage lines. These are labels/context, not fallback world facts. Missing current object locations say `Unknown location`; missing robot position removes its icon from the map; missing room declarations dim the room cards. Missing passage facts use dashed reference lines without arrows. Evidence membership in the sidebar uses the initial roster so evidence does not silently disappear in the effects-only demonstration. The counter measures locations of these known evidence items; it does not infer a logical `goal` fact.

Conflicting locations, holding plus location, empty plus holding, multiple held objects and unmapped rooms are reported. The view does not silently pick a location from conflicting facts. The default illustration is sized for eight rooms and four objects; the sidebar displays all warnings via `inspect` if space runs out. More than three resting objects in one room use a `+N more` label, with the full roster in the sidebar. This is a presentation layout, not an arbitrary-world layout engine.

## Example notebook

Open `World_View_Example.ipynb` with `world_view.py` beside it and Run All. Its first sections use explicitly constructed display fixtures to show initial, carried, delivered and missing states. They are **not evidence that your engine works**. The final cells show how to connect your real engine and domain data. For the final presentation, render your engine's actual WM after each step and keep the required printed facts alongside the image.

No changes to the assignment's `unify`, `substitute`, WorkingMemory or reasoners are required. After copying an updated module into your project, restart the notebook kernel before reimporting.


## Illustrated theme

The included backdrop and transparent Sherlock sprite match the supplied Ravenwick Manor reference. Defaults load relative to the module file, so the notebook can live in a different directory. Assets are embedded as data URIs in each SVG: exported snapshots work offline without external file references. The mansion is decorative context, not a claim about the exact architectural plan. All room cards, passage arrows and entity positions still come from code and the selected facts.

Customise or disable images:

```python
view = WorldView(TASK2_INITIAL_FACTS,
                 background="my_background.png",
                 actor_image="my_robot.png")
# Plain SVG version:
plain = WorldView(TASK2_INITIAL_FACTS, background=False, actor_image=False)
```

Relative custom paths are resolved from the notebook's working directory. The bundled defaults use the module directory. Only local images are read; no web requests are made. Use trusted PNG/JPEG assets.

The example states remain display fixtures, not engine results. For your presentation, call `view.show(wm, t)` on your actual engine's working memory.
