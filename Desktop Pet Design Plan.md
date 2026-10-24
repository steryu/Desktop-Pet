# Desktop Pet: Design Plan

A living document for our Windows desktop pet. Edit freely: change priorities, add ideas, tick things off as we build them.

## Vision

A transparent, always-on-top pet that lives on your desktop. It walks, sleeps, gets hungry, wants attention, and earns you coins you can spend in a store. It starts as a cat drawn from generated shapes, but the code is built so other animals and real artwork can be added later without rewriting the game.

## Technology

- **Language:** Python 3
- **UI framework:** PySide6 (Qt). Gives per-pixel transparency, smooth drawing, sprite support, tray icon, and easy dragging.
- **Save data:** a JSON file in `%APPDATA%\DesktopPet\`
- **Packaging (later):** PyInstaller, one `.exe`

## Architecture principles

1. **Species are plugins.** Everything animal-specific (how it is drawn, its size, walking speed, sounds, favorite food) lives in one species class. The cat is the first. A dog, rabbit, or dragon is a new class, not a rewrite.
2. **Renderer is swappable.** Today the pet is drawn with shapes in code. Later it is drawn from sprite sheets. The pet logic never knows the difference.
3. **Behavior is a state machine.** Walk, sleep, idle, held, falling, eating, playing. Each state has clear rules for when it starts and ends.
4. **Stats are separate from visuals.** Hunger, energy, and affection are plain numbers that save and load independently.
5. **Everything in the world is an object.** Bed, bowl, toys, and store items share one furniture system.
6. **Data-driven items.** Store items and food types are defined in data (name, price, effect), so adding one doesn't need new code paths.

## Planned file layout

- `main.py`: starts the app
- `pet.py`: the pet window, state machine, and behavior
- `species/cat.py`: cat drawing and traits (more species later)
- `stats.py`: hunger, energy, affection, mood
- `save.py`: load and save game data
- `furniture.py`: bed, bowl, toys (Phase 3)
- `store.py`: items and coins (Phase 5)

## Phases

### Phase 1: Interaction and foundation

- [ ] Move to PySide6 with a transparent overlay
- [ ] Species system with the cat as the first species
- [ ] State machine: walk, sleep, held, falling
- [ ] Drag and drop with the left mouse button
- [ ] Gravity: dropped pet falls and lands on the taskbar
- [ ] Petting: click for hearts
- [ ] Taskbar-only walking toggle (carried over)
- [ ] Save and load position and settings
- [ ] Right-click menu

### Phase 2: Stats and care

- [ ] Hunger, energy, affection points, and a mood
- [ ] Stats change over time, including while the app is closed (with a cap so a long absence is not cruel)
- [ ] Food bowl and feeding
- [ ] Status bars on hover
- [ ] Affection levels that unlock behaviors
- [ ] Earn coins from care actions (prepares for the store)

### Phase 3: Furniture and home

- [ ] Draggable pet bed; the pet sleeps there when tired and recovers faster
- [ ] Draggable food bowl
- [ ] Toys the pet chases and plays with
- [ ] Shared furniture system for easy new objects

### Phase 4: Personality

- [ ] Idle animations: sit, groom, stretch, yawn, look around
- [ ] Reactions to the mouse cursor
- [ ] Time-of-day behavior (sleepier at night)
- [ ] Speech bubbles
- [ ] Sitting on top of other windows
- [ ] Random events

### Phase 5: Store and economy

- [ ] Coin balance, saved with the pet
- [ ] Store window with categories
- [ ] Buyable items: food types, toys, beds, hats and collars, decorations
- [ ] Inventory and placing items on the desktop
- [ ] Coin sources: daily login bonus, feeding, petting, playing
- [ ] Balanced prices so coins feel earned but not grindy

### Phase 6: Polish and sharing

- [ ] Real sprite art (your own or free packs)
- [ ] Sound effects with a mute option
- [ ] System tray icon and settings window
- [ ] Start with Windows
- [ ] Multi-monitor support
- [ ] Packaged `.exe`

## Store and coins (details to refine)

- Coins are earned through caring for the pet, not only by waiting.
- Items are data entries: name, price, category, effect, and which species can use them.
- Categories to start with: Food, Toys, Furniture, Accessories.
- Possible later: daily deals, limited items, and unlockables tied to affection level.

## Future animals

When we add a second animal, a species defines:

- how it is drawn (shapes or sprite sheet)
- body size and walking speed
- sleeping pose and idle animations
- favorite foods and toys
- unique behaviors (for example a bird that flies, a fish that stays in a bowl)

Ideas: dog, rabbit, hamster, bird, dragon, slime.

## Open questions

- Should a neglected pet only be sad, or are there real consequences?
- Can the player own more than one pet at once?
- Should coins also be earned just by keeping the app running?
- Should there be growth stages (kitten to adult)?

## Ideas parking lot

Add anything here as it comes to you.

-
