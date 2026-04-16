# All Out War: Shogun

## Project Overview

**All Out War: Shogun** is a real-time strategy game where players impersonate a warlord leading a powerful army to conquer the highest national position — the Shogun, the mighty ruler of Japan. Players choose a starting clan from five distinct clans, each with unique specialties, and upgrade their city hall to increase army size.

All goods and resources come from citizens' taxes. Poor financial management can lead to debt, while overtaxing leads to rebellion and the loss of entire cities. The game tests players' strategic abilities in both warfare and financial management.

### Problem the Project Solves

Players must manage warfare and city finances, but the game **lacks a system to clearly track and analyze player actions and resource usage**. As a result, players may not understand why they fall into debt, lose cities, or trigger rebellions.

This project solves this by developing a system that **records player actions and presents the data through graphs and reports**, helping players evaluate their strategies and make better decisions.

### Target Users

Historical strategy game players interested in realistic town management and warfare during the Sengoku period in Japan.

---

## Gameplay

<img width="1920" height="1123" alt="gameplay_map" src="https://github.com/user-attachments/assets/274d3506-2dbd-4c23-9561-f108f84580ac" />


---

## Data Visualization
<img width="1920" height="1097" alt="data_visualization" src="https://github.com/user-attachments/assets/0ad816d3-a8a2-4189-9e37-4bd07b5d548b" />


---

## Key Features

### Actions of Conquest

- **March** — Move armies along routes on the map. Army size dictates range; larger armies march shorter distances. Players and enemies cannot pass obstacles or enemy castles. *Must follow routes.*
- **Attack** *(during march)* — Players or enemies can attack each other's armies if they intercept along routes or by choice.
- **Ambush** *(during march)* — Armies can ambush from forests/bushes. The opponent is forced to fight that turn with no other options.
- **Siege** — Attack a city; defenders include recruited soldiers + default guards (or guards only if no soldiers are present).

### Citizens / Tax (Main Income)

Rage levels range from 1–6 based on tax rate and city level. Tax income scales from `500–1000 × city level multiplier`.

- If `(garrison units × 10) + (soldier units × 10) > tax` → rage resets to default (3) on collection
- If `(garrison units × 10) + (soldier units × 10) < tax` → rage decreases by 1 next turn
- Otherwise → rage increases by +1 every turn

---

## Concept

### Background (Inspiration)

Inspired by *Total War: Shogun 2* by Sega. All Out War: Shogun is a smaller 2D game based on historical actions and events of the Sengoku period.

### Highlight of the Game

The game heavily relies on **real-time strategy gameplay, financial management, and strategic decision-making each turn**. The goal is to conquer Japan and become the Shogun — a challenge mirroring the historical Warring States period.

### Objectives

Conquer all **16 provinces** on the map while overcoming enemy AI factions.

| Condition | Result |
|-----------|--------|
| Conquer all cities | **Win** |
| Player territory reaches 0 | **Lose** |

---

## Object-Oriented Programming Implementation

### UML Class Diagram

<img width="2048" height="1980" alt="uml_class_diagram" src="https://github.com/user-attachments/assets/e414c996-0694-4aa5-b67b-4fb0c7a9bc89" />


### Clan's Default Soldier Info

| Clan | Unit Name | Units | Base Damage | Multiplier |
|------|-----------|-------|-------------|------------|
| Tada | Katana Cavalry | 55 | 10.5 | 1 |
| Date | Odachi Senshi | 60 | 10.0 | 1 |
| Nori | Katana Ashigaru | 180 | 2.9 | 1 |
| Abe | Yari Senshi | 100 | 6.2 | 1 |

### Class: `AIController`

- **Economic Management** — Handles tax collection, pays unit upkeep, and applies periodic difficulty bonuses.
- **Infrastructure & Logistics** — Decides which cities to upgrade and where to recruit, prioritizing border provinces.
- **Strategic Targeting** — Reassesses the best target every turn (prioritizing the player and lost territories).
- **Combat Execution** — Triggers automated battles and sieges based on win probability calculations.

### Class: `City`

Helper: `make_city()` — factory function for instantiating City objects with standardized defaults.

- **Infrastructure Management** — Tracks city level (Village → Citadel) and manages a 3-turn upgrade process.
- **Economic System** — Calculates tax income based on a slider value and city-level multiplier.
- **Public Order (Rage)** — Implements Rage mechanics (differs for player vs. AI), tracking unrest from high taxes, passive drift, and conquest.
- **Production Queues** — Manages soldier recruitment; prevents simultaneous upgrading and recruiting.
- **Defense** — Combines permanent Garrison with stationed soldiers for total defense power.

**Production Queue:**

| Recruiting Soldiers | Upgrading City |
|---|---|
| <img width="363" height="194" alt="production_queue_recruiting" src="https://github.com/user-attachments/assets/d6973da3-0043-481e-b3c1-4f2f163172b0" /> | <img width="145" height="197" alt="production_queue_upgrading" src="https://github.com/user-attachments/assets/aba3e5af-a8e5-4f64-ac97-8343d756075c" /> |

**Economics and Public Order:**

<img width="378" height="376" alt="economics_rage_tax" src="https://github.com/user-attachments/assets/1d7a126e-62a2-4f09-9ed8-178c4fb8b5ae" />


### Class: `Clan`

Helper: `make_clans()` — factory function initializing four primary factions:

- **Tada** — Elite cavalry with high base damage (10.5).
- **Date** — Odachi specialists with high base damage (10.0).
- **Nori** — Overwhelming numbers; 180 units and a 1.30× recruitment bonus.
- **Abe** — Yari formation specialists with strong anti-cavalry bonus.

Additional responsibilities:
- **Resource Management** — Tracks gold reserves and accumulated debt.
- **Military Identity** — Stores unit types, base damage, and `recruit_bonus`.
- **Strategic State** — Tracks clan survival and retake targets for lost home provinces.

### Class: `ForestPoint`

- Forests sit on routes between two specific provinces.
- Tracks which armies are hiding inside.
- Entering a forest hides the army and snaps its position to the forest's coordinates.
- Armies are auto-revealed when they begin marching or leave the connected provinces.

<img width="1534" height="1115" alt="forest_points" src="https://github.com/user-attachments/assets/c6b99c4c-77da-4f5f-a57b-b00f7a604d15" />


### Class: `AmbushEvent`

Handles logic when a marching army enters a route with hidden enemies. Offers two resolutions:

- **Withdraw** — Retreat to origin province; lose all remaining movement.
- **Fight** — Ambushers gain a first-strike bonus; all armies are revealed afterward.

### Class: `GameState`

- **Initialization** — Builds the world: initializes clans, assigns cities, spawns starting forces.
- **City & Province Management** — Maps provinces to owners and sets garrison stats per clan.
- **Turn Logic** — Handles turn transitions, triggers AI logic, and processes per-turn logistics.
- **Event Logging** — Maintains `log_messages` for the UI and `data_log` for CSV export.
- **Condition Checking** — Detects clan eliminations and win conditions.
- **Warning System** — Warns players how many turns remain before a revolt triggers.
- **Rebellion Execution** — Converts rebelling cities to the "Rebels" faction.
- **Army Tracking** — Manages a global list of `MapArmy` objects.
- **Ambush Detection** — Uses `check_ambush` to detect hidden unit interactions.
- **Data Captured** — Logs military power and territory count for every active clan per turn.
- **Performance Metrics** — Tracks player-specific gold reserves and soldier counts.

### Class: `MapArmy`

- **Position Tracking** — Tracks province location or mid-route position via kilometer-based coordinates.
- **Movement Logic** — Calculates travel progress based on army size, terrain (e.g., mountains), and clan bonuses (e.g., Tada speed boost).
- **Pathfinding** — Uses **BFS (Breadth-First Search)** for long-distance march queues.
- **Combat Readiness** — Tracks exhaustion after capturing a province or completing a siege.
- **Stealth** — Manages hidden status in forest terrain.
- **Rendering** — `screen_pos()` returns exact `(x, y)` pixel coordinates for a 960×720 canvas with smooth interpolation.

| Enemy BFS | Player Marching |
|---|---|
| <img width="758" height="528" alt="enemy_bfs" src="https://github.com/user-attachments/assets/35d94d43-e5de-4d74-b65e-1b8c2d3c95b8" /> | <img width="681" height="425" alt="player_marching" src="https://github.com/user-attachments/assets/909c9ad8-937f-4b97-b49f-e9a0ca820a1a" /> |

### Class: `Troops`

- Stores name, owner, unit count, and base damage per unit.
- `power()` = `Units × Damage`

### Class: `Soldier(Troops)`

- `multiplier_power` attribute for temporary buffs/debuffs.
- `take_damage()` reduces unit count based on opponent power.
- `maintenance_cost()` = 10 gold per unit.
- `is_alive()` checks if unit count > 0.

### Class: `Garrison(Troops)`

- Static defense unit with no damage-taking logic.
- Focuses on a static `power()` value and `maintenance_cost()`.

| Feature | Soldier (Troops) | Garrison (Troops) |
|---------|-----------------|-------------------|
| Movement | Mobile (Field Armies) | Stationary (Defenders) |
| Power Formula | Units × Damage × Multiplier | Units × Damage |
| Cost | 10 per unit | 10 per unit |
| Health | Can die | Static |

### Class: `StatsLogger`

- **Automatic CSV Creation** — Generates a uniquely named CSV per session (e.g., `Game_1_16-4-2026.csv`).
- **Event Logging** — Captures `RECRUIT`, `BATTLE_WIN`, `SIEGE_WIN`, and `REBELLION` events.
- **Timer System** — Tracks `time_elapsed` per turn to analyze decision-making speed.

<img width="222" height="116" alt="csv_creation" src="https://github.com/user-attachments/assets/6d52faa6-261d-4aa7-bbd7-34dbf0c32f46" />


---

## Data Feature

Every player action is logged as its own row. A 20-turn game produces roughly **100–200 rows** (e.g., each battle logs 2 rows, each recruit logs 1 row). This **raw data** is the base for **5 graphs** and **1 summary table**.

All graph features are derived by filtering the `event_type` column — no data is duplicated.

Players can load statistics from previously completed games (each stored as a separate CSV) to regenerate graphs and tables for analysis.

### Raw Data Structure Example

| turn | time | event_type | clan | province | units | provinces |
|------|------|------------|------|----------|-------|-----------|
| 3 | 12.4 | RECRUIT | Tada | Kyoto | 55 | 2 |
| 3 | 15.2 | BATTLE | Tada | Musashi | 0 | 3 |

### Data Features

| Feature | Objective | Method | Source | Display |
|---------|-----------|--------|--------|---------|
| Soldiers Recruited vs Lost | Measure recruitment efficiency and bot difficulty | Log 1 row per RECRUIT and BATTLE event | `game.py` | Stacked Bar Chart |
| Damage Dealt vs Taken | Compare total damage for player vs AI | Log 1 row per BATTLE/SIEGE/AMBUSH per side | `game.py` | Scatter Plot |
| Cities Gained vs Lost | Measure territorial efficiency and bot difficulty | Log 1 row per SIEGE_WIN/SIEGE_LOSS | `game.py` | Bar Chart |
| Military Growth Over Time | Show overall power growth across turns | Log 1 row per clan per turn (end snapshot) | `clans.py` | Cumulative Line Chart |
| Time Per Turn | Track average playtime per turn | Log 1 row per turn with elapsed seconds | `game.py` | Line Chart |

---

## Data Recording Method

Data is recorded to a CSV file per game in the format `game[#]_day-month-year`. A new CSV is created for each new game session.

**Examples:**
- `Game_1_29-3-2026.csv`
- `Game_2_30-3-2026.csv`

---

## Data Analysis Report

Displayed in-depth after the game ends (win or loss). Generated in-game using graph plotters.

### Summary Table Example

| Metric | Value |
|--------|-------|
| Total Turns | 120 |
| Soldiers Recruited | 1,250 |
| Soldiers Lost | 980 |
| Cities Gained | 12 |
| Cities Lost | 8 |
| Total Damage Dealt | 5,430 |
| Total Damage Taken | 4,870 |
| Game Result | Win |

### Graph Analysis Criteria

| Feature | Objective | Type | X-Axis | Y-Axis |
|---------|-----------|------|--------|--------|
| Soldiers Recruited vs Lost | Comparison of both subjects | Stacked Bar Chart | Turns | Number of soldiers |
| Damage Dealt vs Taken | Comparison of both subjects | Scatter Plot | Turns | Damage values |
| Cities Gained vs Lost | Comparison of both subjects | Bar Chart | Turns | Number of cities |
| Military Growth | Show power growth over time | Cumulative Line Chart | Turns | Clan's power |
| Time Per Turn | Measure time spent per turn | Line Chart | Turns | Time (seconds) |

---

## Developers Debugging

- Statistics include debug mode with mock-up data for display testing.
- Triggers the game state to end and shows statistical mock-up data.

---

## Document Version History

| Version | Date | Editor |
|---------|------|--------|
| 1.1 | 12 March 2025 | Phunnipath Theankaew |
| 1.2 | 21 March 2025 | Phunnipath Theankaew |
