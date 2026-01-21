# Mossad Bot Training System

This folder contains all files related to the MossadBot and its automated training system.

## Files

- **`mossad_bot.py`** - The bot itself (located in `../bots/mossad_bot.py`)
- **`train_bot.py`** - Main training script
- **`test_runner.py`** - Runs games and collects statistics
- **`pattern_analyzer.py`** - Analyzes failure patterns
- **`code_generator.py`** - Generates bot improvements
- **`training_log.json`** - Training history and results
- **`AI_TRAINING_PROMPT.md`** - Prompt for AI to improve the training system
- **`TRAINING_SYSTEM_README.md`** - Documentation for the training system

## Usage

Run training from the project root:

```bash
py mossad/train_bot.py --target-win-rate 0.50 --max-iterations 20 --games-per-iteration 100
```

Or from the mossad folder:

```bash
cd mossad
py train_bot.py --target-win-rate 0.50 --max-iterations 20 --games-per-iteration 100
```

## Structure

The bot file itself remains in `bots/mossad_bot.py` as that's the standard location for all bots. The training system files are organized here for better project structure.
