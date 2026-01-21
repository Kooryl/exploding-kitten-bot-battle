"""
Automated Bot Training System for 5-Player Battle Royale

Trains mossad_bot.py to achieve target win rate in 1v4 battle royale format.
"""

import argparse
import json
from pathlib import Path

from code_generator import CodeGenerator
from pattern_analyzer import PatternAnalyzer
from test_runner import TestRunner


def main() -> None:
    """Main training loop."""
    parser = argparse.ArgumentParser(
        description="Automated bot training system for 5-player battle royale"
    )
    parser.add_argument(
        "--target-win-rate",
        type=float,
        default=0.50,
        help="Target win rate (default: 0.50 = 50%%)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Maximum training iterations (default: 20)",
    )
    parser.add_argument(
        "--games-per-iteration",
        type=int,
        default=100,
        help="Number of games per iteration (default: 100)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="training_log.json",
        help="Path to training log file (default: training_log.json)",
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AUTOMATED BOT TRAINING SYSTEM - 5-PLAYER BATTLE ROYALE")
    print("=" * 70)
    print(f"Format: 1 MossadBot vs 4 RandomBots")
    print(f"Target Win Rate: {args.target_win_rate*100:.1f}%")
    print(f"Max Iterations: {args.max_iterations}")
    print(f"Games per Iteration: {args.games_per_iteration}")
    print("=" * 70)
    print()
    
    # Initialize components
    runner = TestRunner(games_to_run=args.games_per_iteration)
    analyzer = PatternAnalyzer()
    generator = CodeGenerator()
    
    # Training log
    training_log: list[dict[str, Any]] = []
    
    # Initial generation to ensure file exists
    generator.generate_improvements({}, 0.0)
    
    # Initial test
    print("--- Initial Test ---")
    results = runner.run_tests()
    initial_win_rate = results["win_rate"]
    initial_avg_place = results["avg_placement"]
    print(f"Initial Win Rate: {initial_win_rate:.1%}")
    print(f"Initial Avg Placement: {initial_avg_place:.1f}")
    print(f"Placement Distribution: {results['placement_distribution']}\n")
    
    training_log.append({
        "iteration": 0,
        "win_rate": initial_win_rate,
        "avg_placement": initial_avg_place,
        "wins": results["wins"],
        "losses": results["losses"],
        "placement_distribution": results["placement_distribution"],
        "note": "Initial baseline",
        "params": generator.params.copy(),
    })
    
    if initial_win_rate >= args.target_win_rate:
        print(f"SUCCESS! Bot already achieves target win rate: {initial_win_rate:.1%}")
        return
    
    # Training loop
    for iteration in range(1, args.max_iterations + 1):
        print(f"--- Iteration {iteration}/{args.max_iterations} ---")
        
        # 1. Run tests
        results = runner.run_tests()
        win_rate = results["win_rate"]
        avg_place = results["avg_placement"]
        
        # 2. Analyze patterns
        analysis = analyzer.analyze(results)
        print(f"Win Rate: {win_rate:.1%} | Avg Place: {avg_place:.1f}")
        print(f"Analysis: Early Death: {analysis.get('rate_early_death', 0):.1%}, "
              f"Hoarding Death: {analysis.get('rate_hoarding_death', 0):.1%}, "
              f"Starvation: {analysis.get('rate_starvation', 0):.1%}, "
              f"Late Death: {analysis.get('rate_late_death', 0):.1%}")
        print(f"Placement Distribution: {results['placement_distribution']}")
        
        # Log iteration
        training_log.append({
            "iteration": iteration,
            "win_rate": win_rate,
            "avg_placement": avg_place,
            "wins": results["wins"],
            "losses": results["losses"],
            "placement_distribution": results["placement_distribution"],
            "analysis": analysis,
            "params": generator.params.copy(),
        })
        
        # 3. Check if target achieved
        if win_rate >= args.target_win_rate:
            print(f"\n{'='*70}")
            print(f"SUCCESS! Target win rate achieved: {win_rate:.1%}")
            print(f"{'='*70}")
            break
        
        # 4. Generate and apply improvements
        print("Generating improvements...")
        changes = generator.generate_improvements(analysis, win_rate)
        print(f"Changes: {', '.join(changes)}")
        print(f"New Parameters: {generator.params}")
        print()
        
        # Save log periodically
        if iteration % 5 == 0:
            log_path = Path(args.log_file)
            log_path.write_text(json.dumps(training_log, indent=2))
            print(f"Training log saved to {log_path}\n")
    
    # Final validation
    print("\n--- Final Validation (200 games) ---")
    final_runner = TestRunner(games_to_run=200)
    final_results = final_runner.run_tests()
    final_win_rate = final_results["win_rate"]
    final_avg_place = final_results["avg_placement"]
    
    print(f"\n{'='*70}")
    print("TRAINING COMPLETE")
    print(f"{'='*70}")
    print(f"Final Win Rate: {final_win_rate:.1%}")
    print(f"Final Avg Placement: {final_avg_place:.1f}")
    print(f"Target Win Rate: {args.target_win_rate*100:.1f}%")
    print(f"Placement Distribution: {final_results['placement_distribution']}")
    
    if final_win_rate >= args.target_win_rate:
        print("SUCCESS! TARGET ACHIEVED!")
    else:
        print("WARNING: TARGET NOT REACHED - Continue training or adjust strategy")
    
    # Save final log
    log_path = Path(args.log_file)
    training_log.append({
        "iteration": "final",
        "win_rate": final_win_rate,
        "avg_placement": final_avg_place,
        "wins": final_results["wins"],
        "losses": final_results["losses"],
        "placement_distribution": final_results["placement_distribution"],
        "note": "Final validation (200 games)",
        "params": generator.params.copy(),
    })
    log_path.write_text(json.dumps(training_log, indent=2))
    print(f"\nTraining log saved to {log_path}")


if __name__ == "__main__":
    main()
