"""
Auto-Improve Bot Script - Analyze games and automatically improve MossadBot.

This script:
1. Runs games and analyzes performance
2. Identifies weaknesses
3. Automatically improves the bot code
"""

import re
from pathlib import Path
from typing import Any

from analyze_bot import analyze_games, print_analysis


def suggest_bot_improvements(analysis: dict[str, Any], bot_path: str) -> list[str]:
    """Generate specific code improvement suggestions."""
    suggestions: list[str] = []
    
    win_rate = analysis['win_rate']
    explosions_in_losses = analysis['explosions_in_losses']
    losses = analysis['losses']
    drew_kitten_in_losses = analysis['drew_kitten_in_losses']
    
    # Analyze action frequencies
    win_actions = analysis.get('win_actions', {})
    loss_actions = analysis.get('loss_actions', {})
    
    skip_win = win_actions.get("SkipCard", 0)
    skip_loss = loss_actions.get("SkipCard", 0)
    total_skip = skip_win + skip_loss
    
    attack_win = win_actions.get("AttackCard", 0)
    attack_loss = loss_actions.get("AttackCard", 0)
    total_attack = attack_win + attack_loss
    
    combo_win = sum(1 for k in win_actions.keys() if "COMBO" in str(k))
    combo_loss = sum(1 for k in loss_actions.keys() if "COMBO" in str(k))
    total_combo = combo_win + combo_loss
    
    # Generate specific suggestions
    if win_rate < 90:
        suggestions.append(f"Win rate is {win_rate:.1f}% - target is 90%+")
    
    if explosions_in_losses > losses * 0.5:
        suggestions.append(f"{explosions_in_losses}/{losses} losses involved explosions - need better Defuse management")
    
    if drew_kitten_in_losses > losses * 0.7:
        suggestions.append(f"{drew_kitten_in_losses}/{losses} losses involved drawing Exploding Kitten - use Skip/Attack more aggressively")
    
    if total_skip < analysis['total_games'] * 0.4:
        suggestions.append(f"Skip cards used {total_skip} times - should use Skip more to avoid drawing")
    
    if total_attack < analysis['total_games'] * 0.3:
        suggestions.append(f"Attack cards used {total_attack} times - should use Attack more to force opponent draws")
    
    if total_combo < analysis['total_games'] * 0.5:
        suggestions.append(f"Combos used {total_combo} times - should use combos more to steal Defuse")
    
    # Calculate effectiveness
    if skip_win + skip_loss > 0:
        skip_effectiveness = skip_win / (skip_win + skip_loss) if (skip_win + skip_loss) > 0 else 0
        if skip_effectiveness < 0.6:
            suggestions.append(f"Skip effectiveness: {skip_effectiveness*100:.1f}% - Skip usage may not be optimal")
    
    if attack_win + attack_loss > 0:
        attack_effectiveness = attack_win / (attack_win + attack_loss) if (attack_win + attack_loss) > 0 else 0
        if attack_effectiveness < 0.6:
            suggestions.append(f"Attack effectiveness: {attack_effectiveness*100:.1f}% - Attack usage may not be optimal")
    
    return suggestions


def improve_bot_code(bot_path: str, suggestions: list[str]) -> str:
    """Generate improved bot code based on suggestions."""
    bot_code = Path(bot_path).read_text()
    
    improvements: list[str] = []
    
    # Check if we need to be more aggressive with Skip
    if any("Skip" in s for s in suggestions):
        # Find the Skip priority section
        if 'if skip_cards and defuse_count == 0:' in bot_code:
            improvements.append("Skip usage when 0 Defuse is already implemented")
        else:
            improvements.append("Add: Always use Skip when defuse_count == 0")
    
    # Check if we need more Attack usage
    if any("Attack" in s for s in suggestions):
        if 'if attack_cards and view.other_players:' in bot_code:
            improvements.append("Attack usage is implemented - may need to be higher priority")
        else:
            improvements.append("Add: Always play Attack cards when available")
    
    # Check combo usage
    if any("combo" in s.lower() for s in suggestions):
        if '_find_three_of_kind' in bot_code:
            improvements.append("Combo detection is implemented - may need to use more frequently")
        else:
            improvements.append("Add: More aggressive combo usage")
    
    return "\n".join(improvements)


def main() -> None:
    """Main improvement function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze and improve bot")
    parser.add_argument(
        "--games",
        type=int,
        default=50,
        help="Number of games to analyze (default: 50)",
    )
    parser.add_argument(
        "--bot1",
        type=str,
        default="bots/mossad_bot.py",
        help="Path to bot to improve (default: bots/mossad_bot.py)",
    )
    parser.add_argument(
        "--bot2",
        type=str,
        default="bots/random_bot.py",
        help="Path to opponent bot (default: bots/random_bot.py)",
    )
    parser.add_argument(
        "--auto-improve",
        action="store_true",
        help="Automatically apply improvements to bot code",
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("BOT ANALYSIS AND IMPROVEMENT TOOL")
    print("=" * 70)
    print()
    
    # Run analysis
    analysis = analyze_games(args.games, args.bot1, args.bot2)
    
    # Print results
    print_analysis(analysis)
    
    # Generate improvement suggestions
    print("\n" + "=" * 70)
    print("DETAILED IMPROVEMENT SUGGESTIONS")
    print("=" * 70)
    
    suggestions = suggest_bot_improvements(analysis, args.bot1)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    
    # Generate code improvements
    code_improvements = improve_bot_code(args.bot1, suggestions)
    if code_improvements:
        print("\n" + "=" * 70)
        print("CODE IMPROVEMENTS NEEDED")
        print("=" * 70)
        print(code_improvements)
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nCurrent Win Rate: {analysis['win_rate']:.2f}%")
    print(f"Target Win Rate: 90%+")
    
    if analysis['win_rate'] >= 90:
        print("\n[SUCCESS] Bot is performing at target level!")
    else:
        print(f"\n[ACTION NEEDED] Bot needs {90 - analysis['win_rate']:.1f}% improvement")
        print("Review suggestions above and update bot code accordingly.")


if __name__ == "__main__":
    main()
