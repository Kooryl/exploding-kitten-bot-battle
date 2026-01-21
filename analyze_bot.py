"""
Bot Analysis Script - Analyze game performance and suggest improvements.

This script runs multiple games, analyzes the results, and provides
insights for improving MossadBot's win rate.
"""

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from game.engine import GameEngine
from game.history import EventType


def run_game_with_history(seed: int, bot1_path: str, bot2_path: str) -> dict[str, Any]:
    """Run a single game and return detailed statistics."""
    from game.bots.loader import BotLoader
    
    engine = GameEngine(seed=seed, quiet_mode=True, chat_enabled=False)
    loader = BotLoader()
    
    # Load bots
    bot1 = loader.load_from_file(Path(bot1_path))[0]
    bot2 = loader.load_from_file(Path(bot2_path))[0]
    
    bot1_base_name = bot1.name
    bot2_base_name = bot2.name
    
    engine.add_bot(bot1)
    engine.add_bot(bot2)
    
    # Get actual player IDs (may have suffixes)
    bot1_id = None
    bot2_id = None
    for pid in engine._bots.keys():
        if pid.startswith(bot1_base_name):
            bot1_id = pid
        elif pid.startswith(bot2_base_name):
            bot2_id = pid
    
    # Run game
    winner = engine.run()
    
    # Analyze events
    events = engine.history.get_events()
    
    # Extract statistics
    stats: dict[str, Any] = {
        "winner": winner,
        "seed": seed,
        "bot1_base_name": bot1_base_name,
        "bot2_base_name": bot2_base_name,
        "bot1_id": bot1_id,
        "bot2_id": bot2_id,
        "total_turns": 0,
        "bot1_actions": [],
        "bot2_actions": [],
        "bot1_defuse_count": 0,
        "bot2_defuse_count": 0,
        "bot1_exploded": False,
        "bot2_exploded": False,
        "bot1_card_counts": [],
        "bot2_card_counts": [],
        "bot1_drew_kitten": False,
        "bot2_drew_kitten": False,
    }
    
    for event in events:
        if event.event_type == EventType.TURN_START:
            stats["total_turns"] += 1
        
        if event.event_type == EventType.CARD_PLAYED:
            player_id = event.player_id
            card_type = event.data.get("card_type", "")
            
            if player_id == bot1_id:
                stats["bot1_actions"].append(card_type)
            elif player_id == bot2_id:
                stats["bot2_actions"].append(card_type)
        
        if event.event_type == EventType.COMBO_PLAYED:
            player_id = event.player_id
            if player_id == bot1_id:
                stats["bot1_actions"].append("COMBO")
            elif player_id == bot2_id:
                stats["bot2_actions"].append("COMBO")
        
        if event.event_type == EventType.EXPLODING_KITTEN_DRAWN:
            player_id = event.player_id
            if player_id == bot1_id:
                stats["bot1_drew_kitten"] = True
            elif player_id == bot2_id:
                stats["bot2_drew_kitten"] = True
        
        if event.event_type == EventType.PLAYER_ELIMINATED:
            player_id = event.player_id
            if player_id == bot1_id:
                stats["bot1_exploded"] = True
            elif player_id == bot2_id:
                stats["bot2_exploded"] = True
    
    return stats


def analyze_games(num_games: int = 100, bot1_path: str = "bots/mossad_bot.py", bot2_path: str = "bots/random_bot.py") -> dict[str, Any]:
    """Run multiple games and analyze results."""
    print(f"Running {num_games} games for analysis...")
    print(f"Bot 1: {bot1_path}")
    print(f"Bot 2: {bot2_path}\n")
    
    wins = 0
    losses = 0
    all_stats: list[dict[str, Any]] = []
    
    for i in range(num_games):
        seed = (i * 1000) % (2**31)
        try:
            stats = run_game_with_history(seed, bot1_path, bot2_path)
            all_stats.append(stats)
            
            # Check if winner is bot1 (could be "MossadBot" or "MossadBot_2")
            bot1_base_name = stats.get("bot1_base_name", "")
            winner = stats.get("winner", "")
            if winner and bot1_base_name and winner.startswith(bot1_base_name):
                wins += 1
            else:
                losses += 1
            
            if (i + 1) % 10 == 0:
                win_rate = (wins / (i + 1)) * 100
                print(f"Progress: {i + 1}/{num_games} games | Win rate: {win_rate:.1f}%")
        except Exception as e:
            print(f"Error in game {i + 1}: {e}")
            continue
    
    win_rate = (wins / num_games) * 100
    
    # Analyze patterns
    # Get bot1 base name from first game
    bot1_base_name = all_stats[0].get("bot1_base_name", "") if all_stats else ""
    
    # Check winner - it could be bot1_id or bot2_id depending on order
    win_stats = []
    loss_stats = []
    for s in all_stats:
        winner = s.get("winner", "")
        bot1_id = s.get("bot1_id", "")
        # Winner matches bot1 if it starts with bot1_base_name
        if winner and bot1_id and (winner == bot1_id or winner.startswith(bot1_base_name)):
            win_stats.append(s)
        else:
            loss_stats.append(s)
    
    # Count actions in wins vs losses
    win_actions = Counter()
    loss_actions = Counter()
    
    for stat in win_stats:
        for action in stat.get("bot1_actions", []):
            win_actions[action] += 1
    
    for stat in loss_stats:
        for action in stat.get("bot1_actions", []):
            loss_actions[action] += 1
    
    # Analyze explosion patterns
    explosions_in_losses = sum(1 for s in loss_stats if s.get("bot1_exploded", False))
    explosions_in_wins = sum(1 for s in win_stats if s.get("bot1_exploded", False))
    
    # Analyze when bot drew kitten
    drew_kitten_in_losses = sum(1 for s in loss_stats if s.get("bot1_drew_kitten", False))
    drew_kitten_in_wins = sum(1 for s in win_stats if s.get("bot1_drew_kitten", False))
    
    analysis = {
        "total_games": num_games,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "explosions_in_losses": explosions_in_losses,
        "explosions_in_wins": explosions_in_wins,
        "drew_kitten_in_losses": drew_kitten_in_losses,
        "drew_kitten_in_wins": drew_kitten_in_wins,
        "win_actions": dict(win_actions),
        "loss_actions": dict(loss_actions),
        "avg_turns_in_wins": sum(s.get("total_turns", 0) for s in win_stats) / len(win_stats) if win_stats else 0,
        "avg_turns_in_losses": sum(s.get("total_turns", 0) for s in loss_stats) / len(loss_stats) if loss_stats else 0,
    }
    
    return analysis


def print_analysis(analysis: dict[str, Any]) -> None:
    """Print analysis results and suggestions."""
    print("\n" + "=" * 70)
    print("BOT ANALYSIS RESULTS")
    print("=" * 70)
    
    print(f"\nWin Rate: {analysis['win_rate']:.2f}%")
    print(f"Wins: {analysis['wins']} | Losses: {analysis['losses']}")
    
    print(f"\nAverage Turns:")
    print(f"  Wins: {analysis['avg_turns_in_wins']:.1f}")
    print(f"  Losses: {analysis['avg_turns_in_losses']:.1f}")
    
    print(f"\nExplosion Analysis:")
    print(f"  Exploded in losses: {analysis['explosions_in_losses']}/{analysis['losses']}")
    print(f"  Exploded in wins: {analysis['explosions_in_wins']}/{analysis['wins']}")
    print(f"  Drew kitten in losses: {analysis['drew_kitten_in_losses']}/{analysis['losses']}")
    print(f"  Drew kitten in wins: {analysis['drew_kitten_in_wins']}/{analysis['wins']}")
    
    print(f"\nAction Frequency (Wins):")
    win_actions = analysis['win_actions']
    if win_actions:
        for action, count in sorted(win_actions.items(), key=lambda x: -x[1])[:10]:
            print(f"  {action}: {count}")
    else:
        print("  (no actions recorded)")
    
    print(f"\nAction Frequency (Losses):")
    loss_actions = analysis['loss_actions']
    if loss_actions:
        for action, count in sorted(loss_actions.items(), key=lambda x: -x[1])[:10]:
            print(f"  {action}: {count}")
    else:
        print("  (no actions recorded)")
    
    # Generate suggestions
    print("\n" + "=" * 70)
    print("SUGGESTIONS FOR IMPROVEMENT")
    print("=" * 70)
    
    suggestions: list[str] = []
    
    if analysis['win_rate'] < 90:
        suggestions.append("[!] Win rate below 90% - needs optimization")
    
    if analysis['explosions_in_losses'] > analysis['losses'] * 0.5:
        suggestions.append("[!] High explosion rate in losses - improve Defuse management")
    
    if analysis['drew_kitten_in_losses'] > analysis['losses'] * 0.7:
        suggestions.append("[!] Drawing Exploding Kittens frequently - use Skip/Attack more")
    
    # Compare action frequencies
    total_attacks = win_actions.get("AttackCard", 0) + loss_actions.get("AttackCard", 0)
    if total_attacks > 0:
        attack_win_rate = win_actions.get("AttackCard", 0) / total_attacks
        if attack_win_rate < 0.6:
            suggestions.append("[TIP] Attack cards may not be used optimally")
    
    skip_usage = win_actions.get("SkipCard", 0) + loss_actions.get("SkipCard", 0)
    if skip_usage < analysis['total_games'] * 0.3:
        suggestions.append("[TIP] Consider using Skip cards more to avoid drawing")
    
    combo_usage = sum(win_actions.get(k, 0) + loss_actions.get(k, 0) for k in win_actions.keys() if "COMBO" in str(k))
    if combo_usage < analysis['total_games'] * 0.5:
        suggestions.append("[TIP] Consider using combos more frequently to steal Defuse")
    
    if not suggestions:
        suggestions.append("[OK] Bot is performing well! Current strategy seems optimal.")
    
    for suggestion in suggestions:
        print(f"  {suggestion}")
    
    print("\n" + "=" * 70)


def main() -> None:
    """Main analysis function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze bot performance")
    parser.add_argument(
        "--games",
        type=int,
        default=100,
        help="Number of games to analyze (default: 100)",
    )
    parser.add_argument(
        "--bot1",
        type=str,
        default="bots/mossad_bot.py",
        help="Path to first bot (default: bots/mossad_bot.py)",
    )
    parser.add_argument(
        "--bot2",
        type=str,
        default="bots/random_bot.py",
        help="Path to second bot (default: bots/random_bot.py)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save analysis to JSON file",
    )
    
    args = parser.parse_args()
    
    # Run analysis
    analysis = analyze_games(args.games, args.bot1, args.bot2)
    
    # Print results
    print_analysis(analysis)
    
    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"\nAnalysis saved to {args.output}")


if __name__ == "__main__":
    main()
