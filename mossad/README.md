# Mossad Bot Training System (Original)

This folder contains the **parameter-based** training system for the original MossadBot.

> **Looking for MossadBotAdvanced?** See `../mossad_advanced/` for the weighted utility agent with Hill Climbing optimization.

## Bot

- **`../bots/mossad_bot.py`** - Original MossadBot (parameter-based)

## Training System Files

| File | Description |
|------|-------------|
| `train_bot.py` | Main training script |
| `test_runner.py` | Runs games and collects statistics |
| `pattern_analyzer.py` | Analyzes failure patterns |
| `code_generator.py` | Generates bot improvements |
| `training_log.json` | Training results |

## Usage

```bash
py mossad/train_bot.py --target-win-rate 0.50 --max-iterations 20 --games-per-iteration 100
```

## How It Works

1. **Test Runner**: Runs 100 games (1 MossadBot vs 4 RandomBots)
2. **Pattern Analyzer**: Identifies failure patterns:
   - `rate_early_death`: Died 4th/5th place
   - `rate_hoarding_death`: Died with cards but no Defuse
   - `rate_starvation`: Died without Defuse
   - `rate_late_death`: Died 2nd/3rd place
3. **Code Generator**: Adjusts parameters based on analysis:
   - `crowd_panic_threshold`: Panic level with 3+ players
   - `duel_panic_threshold`: Panic level with 2 players
   - `aggression_bias`: Probability of aggressive plays
   - `hoard_pairs`: Whether to save pairs for stealing
   - `combo_priority`: Priority multiplier for combos
   - `skip_priority`: Priority multiplier for Skip cards
4. **Repeat**: Until target win rate achieved

## File Structure

```
mossad/
├── __init__.py              # Package init
├── README.md                # This file
├── AI_TRAINING_PROMPT.md    # AI training prompt
├── TRAINING_SYSTEM_README.md # Detailed training docs
│
├── train_bot.py             # Main trainer
├── test_runner.py           # Game runner
├── pattern_analyzer.py      # Failure analyzer
├── code_generator.py        # Code generator
└── training_log.json        # Results log
```

## Comparison with MossadBotAdvanced

| Feature | MossadBot (This) | MossadBotAdvanced |
|---------|------------------|-------------------|
| Location | `mossad/` | `mossad_advanced/` |
| Bot File | `bots/mossad_bot.py` | `bots/mossad_bot_advanced.py` |
| Logic | if-else parameters | Utility weights |
| Training | Pattern analysis | Hill climbing |
| Speed | Fast | Slower but smarter |

For new development, consider using `mossad_advanced/` which has more sophisticated optimization.
