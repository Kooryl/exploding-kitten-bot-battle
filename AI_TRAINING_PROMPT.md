# AI Bot Training Prompt

## Objective
Create an automated training system that improves `bots/mossad_bot.py` to achieve **90%+ win rate** against `bots/random_bot.py` in the Exploding Kittens Bot Battle game.

## Current State

### Existing Files
- **`bots/mossad_bot.py`**: Current bot implementation (~67-73% win rate)
- **`analyze_bot.py`**: Analysis tool that runs games and provides statistics
- **`improve_bot.py`**: Improvement suggestion tool
- **`src/game/`**: Game engine (DO NOT MODIFY - only bot code can be changed)

### Current Bot Performance
- Win rate: ~67-73% (target: 90%+)
- All losses involve explosions (drawing Exploding Kittens without Defuse)
- Bot has logic to avoid drawing with 0 Defuse, but still fails in some cases

## Task: Create Automated Training System

### Required Components

1. **Training Script** (`train_bot.py`)
   - Run multiple iterations of bot improvement
   - Each iteration:
     - Run 100+ games to measure current win rate
     - Analyze loss patterns (what actions led to losses)
     - Generate code improvements based on analysis
     - Apply improvements to `bots/mossad_bot.py`
     - Test again
   - Stop when win rate >= 90% or max iterations reached
   - Log all changes and results

2. **Code Generator** (`code_generator.py`)
   - Analyze game statistics and loss patterns
   - Generate Python code improvements for `take_turn()` method
   - Focus on:
     - Never drawing with 0 Defuse (critical!)
     - Better Defuse management
     - More aggressive combo usage to steal Defuse
     - Better hand management
     - Smarter Skip/Attack/Shuffle usage

3. **Pattern Analyzer** (`pattern_analyzer.py`)
   - Deep analysis of game events
   - Identify common failure patterns:
     - When does bot draw Exploding Kittens?
     - What cards did bot have but didn't play?
     - What was the game state when bot lost?
   - Generate specific improvement suggestions

4. **Test Runner** (`test_runner.py`)
   - Run games efficiently (parallel execution)
   - Collect detailed statistics:
     - Win rate
     - Action frequencies
     - Defuse counts at loss
     - Draw pile sizes at loss
     - Hand sizes at loss
   - Return structured data for analysis

### Key Constraints

1. **Only modify bot code** - Never change game engine code
2. **Maintain type safety** - All code must pass `pyright` strict mode
3. **Preserve bot structure** - Keep existing methods, improve logic only
4. **Test thoroughly** - Each change must be validated with 100+ games

### Success Criteria

- Win rate >= 90% over 1000+ games
- All losses analyzed and addressed
- Code is clean, typed, and maintainable
- Training process is reproducible

### Implementation Strategy

1. **Phase 1: Deep Analysis**
   - Enhance `analyze_bot.py` to capture detailed game state at losses
   - Track: hand contents, draw pile size, defuse count, last actions
   - Identify patterns: "Bot lost when it had X cards but drew anyway"

2. **Phase 2: Code Generation**
   - Create templates for common improvements
   - Generate code that:
     - Adds checks before drawing
     - Prioritizes Defuse-stealing combos
     - Uses Skip/Shuffle/See Future more intelligently
   - Apply generated code to bot

3. **Phase 3: Iterative Improvement**
   - Loop: Test → Analyze → Generate → Apply → Test
   - Track win rate over iterations
   - Stop when >= 90% achieved
   - Rollback if win rate decreases

4. **Phase 4: Validation**
   - Run 1000+ games for final validation
   - Ensure consistent 90%+ performance
   - Document final strategy

### Critical Rules to Enforce

1. **NEVER draw with 0 Defuse** - This is the #1 cause of losses
2. **Always try to steal Defuse** - Use combos aggressively
3. **Maintain Defuse buffer** - Try to have 2+ Defuse cards
4. **Avoid drawing when vulnerable** - Use Skip/Shuffle/See Future
5. **Force opponent draws** - Use Attack cards when safe

### Example Improvement Pattern

If analysis shows: "Bot lost 30% of games when it had 0 Defuse and drew"
Then generate code that:
- Checks defuse_count == 0 before ANY draw
- Plays ANY card (even Nope or Cat) to avoid drawing
- Only draws if defuse_count >= 1

### Files to Create

1. `train_bot.py` - Main training loop
2. `code_generator.py` - Generate bot improvements
3. `pattern_analyzer.py` - Analyze loss patterns
4. `test_runner.py` - Efficient game testing
5. `training_config.json` - Configuration for training
6. `training_log.json` - Log of all changes and results

### Expected Output

After training completes:
- `bots/mossad_bot.py` updated with optimized code
- `training_log.json` showing progression to 90%+ win rate
- `final_report.md` documenting the final strategy

## Start Training

Run: `python train_bot.py --target-win-rate 0.90 --max-iterations 50`

The system should automatically:
1. Test current bot
2. Analyze failures
3. Generate improvements
4. Apply changes
5. Test again
6. Repeat until 90%+ achieved
