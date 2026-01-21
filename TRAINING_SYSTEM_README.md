# Automated Bot Training System

## Overview

This training system automatically improves `bots/mossad_bot.py` to achieve 90%+ win rate through iterative testing and code generation.

## Files Created

1. **`test_runner.py`** - Runs games efficiently and collects statistics
2. **`pattern_analyzer.py`** - Analyzes game results to find failure patterns
3. **`code_generator.py`** - Generates code improvements (needs enhancement)
4. **`train_bot.py`** - Main training loop that orchestrates everything

## Usage

### Basic Training
```bash
py train_bot.py --target-win-rate 0.90 --max-iterations 50 --games-per-iteration 100
```

### Quick Test (5 iterations, 50 games each)
```bash
py train_bot.py --target-win-rate 0.80 --max-iterations 5 --games-per-iteration 50
```

### Full Training (90% target)
```bash
py train_bot.py --target-win-rate 0.90 --max-iterations 50 --games-per-iteration 200
```

## How It Works

1. **Initial Test**: Runs games to establish baseline win rate
2. **Analysis**: Analyzes losses to identify failure patterns
3. **Code Generation**: Generates improvements based on analysis
4. **Testing**: Tests improved bot
5. **Iteration**: Repeats until target win rate achieved

## Current Status

✅ **Working Components:**
- Test runner successfully runs games and collects stats
- Pattern analyzer identifies failure patterns (defuse_starvation, etc.)
- Training loop orchestrates the process

⚠️ **Needs Improvement:**
- **Code Generator**: The regex-based code modification is fragile and can create duplicate code. It needs to be smarter about:
  - Understanding the actual code structure
  - Making precise edits without duplicating logic
  - Preserving code quality and type safety

## Known Issues

1. **Code Generator Limitations**: The current regex-based approach doesn't reliably modify the bot file. It may:
   - Create duplicate code blocks
   - Miss patterns it's looking for
   - Break existing logic

2. **Recommendation**: The code generator should be enhanced to:
   - Use AST (Abstract Syntax Tree) parsing for precise code modification
   - Or use a template-based approach where the bot structure is more modular
   - Or generate complete method replacements rather than regex patches

## Next Steps for AI Training

To improve the training system, an AI should:

1. **Enhance Code Generator**:
   - Use `ast` module to parse and modify Python code precisely
   - Create a more structured approach to code generation
   - Test modifications before applying them

2. **Better Pattern Analysis**:
   - Track exact game states at loss points
   - Identify specific decision points where bot made mistakes
   - Generate targeted fixes for specific scenarios

3. **Smarter Strategy Selection**:
   - A/B test different strategies
   - Rollback if win rate decreases
   - Track which strategies work best

## Training Log

Results are saved to `training_log.json` showing:
- Win rate progression
- Applied strategies
- Recommendations
- Final validation results

## Important Notes

- **Never modify game code** - Only bot code (`bots/mossad_bot.py`) should be changed
- **Type safety** - All code must pass `pyright` strict mode
- **Testing** - Each change should be validated with 100+ games
