"""
Tournament Script: Run Mossad Bot against all other bots.

Tests mossad_bot_warfare.py against each other bot individually.
"""

import subprocess
import sys
from pathlib import Path

# All bots to test against
OPPONENT_BOTS = [
    "bots/mossad_bot.py",
    "bots/mossad_bot_advanced.py",
    "bots/mossad_bot_adaptive.py",
    "bots/mossad_bot_advanced_warfare.py",
    "bots/mossad_bot_advanced_v6_backup.py",
    "bots/random_bot.py",
]

MOSSAD_BOT = "bots/mossad_bot_warfare.py"
ITERATIONS = 1000

def run_match(mossad_bot: str, opponent_bot: str, iterations: int) -> dict:
    """Run a match between two bots."""
    print(f"\n{'='*70}")
    print(f"MATCH: Mossad vs {Path(opponent_bot).stem}")
    print(f"{'='*70}\n")
    
    # Set encoding for Windows
    env = {"PYTHONIOENCODING": "utf-8"}
    
    cmd = [
        sys.executable, "-m", "game.main",
        "--stats",
        "--bot", mossad_bot,
        "--bot", opponent_bot + ":4",  # 4 copies of opponent
        "--iterations", str(iterations),
        "--no-chat",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,  # 10 minute timeout per match
        )
        
        # Parse output for win rate
        output = result.stdout + result.stderr
        mossad_wins = 0
        opponent_wins = 0
        
        # Look for win summary
        lines = output.split('\n')
        in_win_summary = False
        for line in lines:
            if "WIN SUMMARY" in line:
                in_win_summary = True
                continue
            if in_win_summary and "Mossad" in line:
                # Parse: "Mossad            291       29.1%"
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        mossad_wins = int(parts[1])
                    except ValueError:
                        pass
            if in_win_summary and "Mossad" not in line and any(bot in line for bot in ["RandomBot", "MossadBot", "MossadBotAdvanced"]):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        opponent_wins = int(parts[1])
                    except ValueError:
                        pass
        
        return {
            "opponent": Path(opponent_bot).stem,
            "mossad_wins": mossad_wins,
            "opponent_wins": opponent_wins,
            "mossad_win_rate": mossad_wins / iterations if iterations > 0 else 0,
            "output": output,
        }
    except subprocess.TimeoutExpired:
        return {
            "opponent": Path(opponent_bot).stem,
            "mossad_wins": 0,
            "opponent_wins": 0,
            "mossad_win_rate": 0,
            "output": "TIMEOUT",
            "error": "Match timed out",
        }
    except Exception as e:
        return {
            "opponent": Path(opponent_bot).stem,
            "mossad_wins": 0,
            "opponent_wins": 0,
            "mossad_win_rate": 0,
            "output": str(e),
            "error": str(e),
        }

def main():
    """Run tournament."""
    print("="*70)
    print("TOURNAMENT: Mossad Bot Warfare vs All Other Bots")
    print("="*70)
    print(f"Testing: {MOSSAD_BOT}")
    print(f"Iterations per match: {ITERATIONS}")
    print(f"Opponents: {len(OPPONENT_BOTS)}")
    print("="*70)
    
    results = []
    
    for opponent in OPPONENT_BOTS:
        if not Path(opponent).exists():
            print(f"\n⚠️ Skipping {opponent} (file not found)")
            continue
        
        result = run_match(MOSSAD_BOT, opponent, ITERATIONS)
        results.append(result)
        
        # Print summary
        print(f"\n📊 Result: Mossad {result['mossad_wins']}-{result['opponent_wins']} {result['opponent']}")
        print(f"   Win Rate: {result['mossad_win_rate']:.1%}")
    
    # Final summary
    print(f"\n{'='*70}")
    print("TOURNAMENT RESULTS")
    print(f"{'='*70}\n")
    
    # Sort by win rate
    results.sort(key=lambda x: x['mossad_win_rate'], reverse=True)
    
    print(f"{'Opponent':<30} {'Mossad Wins':<12} {'Opponent Wins':<15} {'Win Rate':<10}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['opponent']:<30} {r['mossad_wins']:<12} {r['opponent_wins']:<15} {r['mossad_win_rate']:<10.1%}")
    
    # Find best opponent (lowest Mossad win rate = strongest opponent)
    if results:
        weakest_opponent = max(results, key=lambda x: x['mossad_win_rate'])
        strongest_opponent = min(results, key=lambda x: x['mossad_win_rate'])
        
        print(f"\n🏆 Strongest Opponent (hardest for Mossad): {strongest_opponent['opponent']}")
        print(f"   Mossad Win Rate: {strongest_opponent['mossad_win_rate']:.1%}")
        print(f"\n💪 Weakest Opponent (easiest for Mossad): {weakest_opponent['opponent']}")
        print(f"   Mossad Win Rate: {weakest_opponent['mossad_win_rate']:.1%}")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
