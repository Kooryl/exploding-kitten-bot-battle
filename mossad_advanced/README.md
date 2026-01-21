# MossadBot Advanced - Hill Climbing Training System

This folder contains the advanced training system for **MossadBotAdvanced**, a weighted utility agent that uses mathematical coefficients to make decisions.

## Architecture

```
mossad_advanced/
├── __init__.py              # Package init
├── README.md                # This file
├── game_simulator.py        # High-performance parallel game simulator
├── train_hill_climber.py    # Steepest Ascent Hill Climbing optimizer
└── hill_climber_log.json    # Training results (generated)

../bots/
└── mossad_bot_advanced.py   # The bot file (weights updated by trainer)
```

## How It Works

### The Bot (`bots/mossad_bot_advanced.py`)

MossadBotAdvanced uses **utility weights** instead of static if-else logic:

```python
DEFAULT_WEIGHTS = {
    "fear_factor": 0.5,      # How much we fear drawing
    "evasion_value": 0.4,    # Value of Skip/Attack cards
    "info_value": 0.2,       # Value of See the Future
    "greed_value": 0.1,      # Value of stealing cards
    "combo_value": 0.3,      # Value of playing combos
    "favor_value": 0.15,     # Value of Favor cards
    "nope_value": 0.05,      # Value of proactive Nope
    "hand_penalty": 0.02,    # Penalty per card in hand
}
```

**Decision Process:**
1. Calculate `risk` = probability of drawing Exploding Kitten
2. Calculate `draw_cost` = `risk × fear_factor`
3. Score each possible action using weights
4. If `max(action_scores) > draw_cost`: Play that action
5. Else: Draw a card

### The Trainer (`train_hill_climber.py`)

Uses **Steepest Ascent Hill Climbing** to optimize weights:

1. **Test Baseline**: Measure current performance (50 games)
2. **Generate Mutations**: Create 6 weight variants:
   - 🔥 **Aggressive**: ↑greed, ↓fear
   - 😰 **Paranoid**: ↑fear, ↑evasion
   - 🔍 **Analyst**: ↑↑info_value
   - ⚖️ **Balanced**: Random small tweaks
   - 🃏 **Combo Master**: ↑combo, ↑greed
   - 🛡️ **Survivor**: ↑evasion, ↑fear
3. **Test Mutations**: Run 50 games for each
4. **Selection**: If best mutation > baseline, adopt it
5. **File Update**: Rewrite `bots/mossad_bot_advanced.py` with new weights
6. **Repeat**: Until target win rate achieved

### The Simulator (`game_simulator.py`)

High-performance parallel game execution:
- Uses `ProcessPoolExecutor` for parallel games
- Runs 1 MossadBotAdvanced vs 4 RandomBots
- Returns win rate as float (0.0 to 1.0)

## Usage

### Run Training

```bash
# Default: Target 55% win rate, 20 generations
py mossad_advanced/train_hill_climber.py

# Custom settings
py mossad_advanced/train_hill_climber.py --target-win-rate 0.60 --max-generations 30 --games-per-test 100
```

### Test Current Weights

```bash
py -c "from mossad_advanced.game_simulator import GameSimulator; from bots.mossad_bot_advanced import DEFAULT_WEIGHTS; s = GameSimulator(); print(f'Win Rate: {s.run_batch(DEFAULT_WEIGHTS, 100):.1%}')"
```

### Run a Single Game

```bash
py -m game.main --bot bots/mossad_bot_advanced.py bots/random_bot.py:4
```

## Weight Tuning Guide

| Weight | Effect of Increasing |
|--------|---------------------|
| `fear_factor` | More risk-averse, plays more cards before drawing |
| `evasion_value` | Plays Skip/Attack more frequently |
| `info_value` | Uses See the Future more often |
| `greed_value` | More aggressive with stealing (combos) |
| `combo_value` | Prioritizes playing combos |
| `favor_value` | Uses Favor cards more |
| `nope_value` | Uses Nope proactively (generally bad) |
| `hand_penalty` | Dumps cards faster to reduce hand size |

## Training Tips

1. **Start Conservative**: Begin with 50 games per test for speed
2. **Increase Games Later**: Use 100+ games for final validation
3. **Watch for Overfitting**: Small samples can mislead
4. **Multiple Runs**: Run training multiple times to avoid local maxima
5. **Check Logs**: Review `hill_climber_log.json` for insights

## Difference from Original MossadBot

| Feature | MossadBot (Original) | MossadBotAdvanced |
|---------|---------------------|-------------------|
| Decision Logic | if-else statements | Utility calculation |
| Training | Parameter tuning | Weight optimization |
| Adaptability | Limited | Highly tunable |
| Optimization | Rule-based | Mathematical |

The original MossadBot (`../mossad/`) uses discrete parameters and pattern analysis. MossadBotAdvanced uses continuous weights and hill climbing, allowing for more nuanced optimization.
