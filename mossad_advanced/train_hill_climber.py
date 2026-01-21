"""
Hill Climber Training System - Steepest Ascent Optimization

This script implements a Steepest Ascent Hill Climbing algorithm to optimize
the utility weights of MossadBotAdvanced.

The algorithm:
1. Start with baseline weights
2. Generate multiple mutations (variants)
3. Test each variant
4. Select the best performing variant
5. If better than baseline, update and continue
6. Repeat until target win rate achieved or max iterations reached
"""

import argparse
import copy
import json
import random
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from mossad_advanced.game_simulator import GameSimulator


# ============================================================================
# WEIGHT MUTATION STRATEGIES
# ============================================================================

def mutate_aggressive(weights: dict[str, float]) -> dict[str, float]:
    """
    Create an aggressive variant.
    
    Increases greed, combo value, decreases fear.
    """
    mutated = copy.deepcopy(weights)
    mutated["greed_value"] = min(1.0, mutated["greed_value"] * 1.5 + 0.1)
    mutated["combo_value"] = min(1.0, mutated["combo_value"] * 1.3)
    mutated["fear_factor"] = max(0.1, mutated["fear_factor"] * 0.7)
    mutated["evasion_value"] = max(0.1, mutated["evasion_value"] * 0.9)
    return mutated


def mutate_paranoid(weights: dict[str, float]) -> dict[str, float]:
    """
    Create a paranoid (risk-averse) variant.
    
    Increases fear and evasion, decreases greed.
    """
    mutated = copy.deepcopy(weights)
    mutated["fear_factor"] = min(1.0, mutated["fear_factor"] * 1.5 + 0.1)
    mutated["evasion_value"] = min(1.0, mutated["evasion_value"] * 1.3)
    mutated["greed_value"] = max(0.05, mutated["greed_value"] * 0.5)
    mutated["nope_value"] = min(0.5, mutated["nope_value"] * 1.5)
    return mutated


def mutate_analyst(weights: dict[str, float]) -> dict[str, float]:
    """
    Create an information-seeking variant.
    
    Drastically increases info value.
    """
    mutated = copy.deepcopy(weights)
    mutated["info_value"] = min(1.0, mutated["info_value"] * 2.0 + 0.1)
    mutated["fear_factor"] = mutated["fear_factor"] * 1.1
    return mutated


def mutate_balanced(weights: dict[str, float]) -> dict[str, float]:
    """
    Create a balanced variant.
    
    Small random adjustments to all weights.
    """
    mutated = copy.deepcopy(weights)
    for key in mutated:
        delta = random.uniform(-0.1, 0.1)
        mutated[key] = max(0.01, min(1.0, mutated[key] + delta))
    return mutated


def mutate_combo_master(weights: dict[str, float]) -> dict[str, float]:
    """
    Create a combo-focused variant.
    
    Maximizes combo and greed values.
    """
    mutated = copy.deepcopy(weights)
    mutated["combo_value"] = min(1.0, mutated["combo_value"] * 1.5 + 0.15)
    mutated["greed_value"] = min(1.0, mutated["greed_value"] * 1.4)
    mutated["favor_value"] = min(0.5, mutated["favor_value"] * 1.3)
    return mutated


def mutate_survivor(weights: dict[str, float]) -> dict[str, float]:
    """
    Create a survival-focused variant.
    
    Maximizes evasion and fear.
    """
    mutated = copy.deepcopy(weights)
    mutated["evasion_value"] = min(1.0, mutated["evasion_value"] * 1.6)
    mutated["fear_factor"] = min(1.0, mutated["fear_factor"] * 1.4)
    mutated["hand_penalty"] = min(0.1, mutated["hand_penalty"] * 1.5)
    return mutated


# All mutation strategies
MUTATION_STRATEGIES = [
    ("🔥 Aggressive", mutate_aggressive),
    ("😰 Paranoid", mutate_paranoid),
    ("🔍 Analyst", mutate_analyst),
    ("⚖️ Balanced", mutate_balanced),
    ("🃏 Combo Master", mutate_combo_master),
    ("🛡️ Survivor", mutate_survivor),
]


# ============================================================================
# BOT FILE REWRITER
# ============================================================================

BOT_FILE_TEMPLATE = '''"""
MossadBot Advanced - Weighted Utility Agent

This bot uses mathematical utility weights to make decisions rather than
static if-else statements. The weights can be optimized through hill climbing.

Weights are tuned by the training system to maximize win rate.
"""

from typing import TYPE_CHECKING, Any

from game.bots.base import (
    Action,
    Bot,
    DrawCardAction,
    PlayCardAction,
    PlayComboAction,
)
from game.bots.view import BotView
from game.cards.base import Card
from game.history import EventType, GameEvent

if TYPE_CHECKING:
    pass


# ============================================================================
# WEIGHTS - These are optimized by the Hill Climber
# DO NOT MODIFY THIS SECTION MANUALLY - It is rewritten by train_hill_climber.py
# ============================================================================
DEFAULT_WEIGHTS: dict[str, float] = {weights_str}
# ============================================================================


class MossadBotAdvanced(Bot):
    """
    Advanced weighted utility agent for Exploding Kittens.
    
    Decision making is based on comparing action scores against draw cost:
    - If max(action_scores) > draw_cost: Play the best action
    - Else: Draw a card
    
    Weights control the bot's personality:
    - High fear_factor = paranoid, avoids drawing
    - High evasion_value = plays Skip/Attack frequently
    - High greed_value = aggressive stealing
    - High info_value = information-seeking
    """
    
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """
        Initialize the bot with optional custom weights.
        
        Args:
            weights: Custom weight dictionary. If None, uses DEFAULT_WEIGHTS.
        """
        self.weights: dict[str, float] = weights if weights is not None else DEFAULT_WEIGHTS.copy()
        self._last_peek: list[str] = []
        self._opponent_defuse_used: dict[str, int] = {{}}
    
    @property
    def name(self) -> str:
        """Return the bot's display name."""
        return "MossadBotAdvanced"
    
    def _count_defuse(self, hand: tuple[Card, ...]) -> int:
        """Count Defuse cards in hand."""
        return sum(1 for c in hand if c.card_type == "DefuseCard")
    
    def _find_combo(self, hand: tuple[Card, ...], size: int) -> tuple[Card, ...] | None:
        """Find a combo of specified size."""
        combo_cards = [c for c in hand if c.can_combo()]
        if len(combo_cards) < size:
            return None
        
        by_type: dict[str, list[Card]] = {{}}
        for card in combo_cards:
            if card.card_type not in by_type:
                by_type[card.card_type] = []
            by_type[card.card_type].append(card)
        
        for cards in by_type.values():
            if len(cards) >= size:
                return tuple(cards[:size])
        
        return None
    
    def _calculate_risk(self, draw_pile_size: int, num_opponents: int) -> float:
        """
        Calculate the risk of drawing a card.
        
        Risk increases as:
        - Deck gets smaller
        - More opponents have used Defuse (more kittens in deck)
        """
        # Base risk from deck size
        base_risk = 1.0 / max(1, draw_pile_size - num_opponents)
        
        # Adjust for game phase
        if draw_pile_size < 5:
            base_risk *= 2.0  # Very dangerous late game
        elif draw_pile_size < 10:
            base_risk *= 1.5  # Dangerous
        
        return min(1.0, base_risk)
    
    def _calculate_draw_cost(self, risk: float, defuse_count: int) -> float:
        """
        Calculate the cost of drawing a card.
        
        Cost = risk * fear_factor, reduced if we have Defuse protection.
        """
        fear = self.weights["fear_factor"]
        
        # Having Defuse reduces the cost of drawing
        if defuse_count >= 2:
            fear *= 0.3  # Very safe with 2+ Defuse
        elif defuse_count == 1:
            fear *= 0.7  # Somewhat safe with 1 Defuse
        else:
            fear *= 2.0  # Very dangerous with 0 Defuse
        
        return risk * fear
    
    def _score_action(
        self,
        card: Card,
        risk: float,
        defuse_count: int,
        hand_size: int,
        num_opponents: int,
    ) -> float:
        """
        Calculate utility score for playing a card.
        
        Higher scores = more valuable actions.
        """
        card_type = card.card_type
        score = 0.0
        
        # Evasion cards (Skip, Attack) - avoid drawing
        if card_type in ("SkipCard", "AttackCard"):
            score = risk * self.weights["evasion_value"]
            # Attack is slightly better as it forces opponent to draw
            if card_type == "AttackCard" and num_opponents > 0:
                score *= 1.2
        
        # Information cards (See the Future)
        elif card_type == "SeeTheFutureCard":
            score = self.weights["info_value"] * (1.0 + risk)
        
        # Shuffle cards
        elif card_type == "ShuffleCard":
            # Value shuffle more if we saw danger in last peek
            if any("ExplodingKittenCard" in ct for ct in self._last_peek):
                score = risk * self.weights["evasion_value"] * 1.5
            else:
                score = self.weights["info_value"] * 0.5
        
        # Favor cards
        elif card_type == "FavorCard":
            score = self.weights["favor_value"] * (1.0 + risk)
        
        # Nope cards (proactive play - not great but avoids drawing)
        elif card_type == "NopeCard":
            score = self.weights["nope_value"] * risk
        
        # Cat cards (can be played to avoid drawing)
        elif "Cat" in card_type:
            score = self.weights["hand_penalty"] * hand_size * 0.5
        
        # Hand size penalty (encourages playing cards)
        if hand_size > 5:
            score += self.weights["hand_penalty"] * (hand_size - 5)
        
        return score
    
    def _score_combo(
        self,
        combo_size: int,
        risk: float,
        defuse_count: int,
    ) -> float:
        """
        Calculate utility score for playing a combo.
        
        Combos are valuable for stealing cards (especially Defuse).
        """
        base_score = self.weights["combo_value"] * combo_size
        
        # Combos are much more valuable if we need Defuse
        if defuse_count == 0:
            base_score *= 3.0  # Desperate for Defuse
        elif defuse_count == 1:
            base_score *= 1.5  # Would like another Defuse
        
        # Three-of-a-kind is better (can ask for specific card)
        if combo_size >= 3:
            base_score *= 1.5
        
        # Greed factor
        base_score *= (1.0 + self.weights["greed_value"])
        
        return base_score
    
    def take_turn(self, view: BotView) -> Action:
        """
        Make a decision using weighted utility calculation.
        
        Process:
        1. Calculate risk of drawing
        2. Calculate draw cost (risk * fear)
        3. Score all possible actions
        4. If best action score > draw cost, play it
        5. Otherwise, draw
        """
        hand = view.my_hand
        defuse_count = self._count_defuse(hand)
        draw_pile_size = view.draw_pile_count
        num_opponents = len(view.other_players)
        hand_size = len(hand)
        
        # Calculate risk and draw cost
        risk = self._calculate_risk(draw_pile_size, num_opponents)
        draw_cost = self._calculate_draw_cost(risk, defuse_count)
        
        # Score all possible actions
        action_scores: list[tuple[float, Action]] = []
        
        # Score combos first (they use multiple cards)
        three_combo = self._find_combo(hand, 3)
        if three_combo and view.other_players:
            combo_score = self._score_combo(3, risk, defuse_count)
            action_scores.append((
                combo_score,
                PlayComboAction(cards=three_combo, target_player_id=view.other_players[0])
            ))
        
        two_combo = self._find_combo(hand, 2)
        if two_combo and view.other_players:
            combo_score = self._score_combo(2, risk, defuse_count)
            action_scores.append((
                combo_score,
                PlayComboAction(cards=two_combo, target_player_id=view.other_players[0])
            ))
        
        # Score individual cards
        for card in hand:
            # Skip Defuse cards (never play proactively)
            if card.card_type == "DefuseCard":
                continue
            
            # Check if card requires target
            if card.card_type == "FavorCard":
                if view.other_players:
                    score = self._score_action(card, risk, defuse_count, hand_size, num_opponents)
                    action_scores.append((
                        score,
                        PlayCardAction(card=card, target_player_id=view.other_players[0])
                    ))
            elif card.card_type == "AttackCard":
                if view.other_players:
                    score = self._score_action(card, risk, defuse_count, hand_size, num_opponents)
                    action_scores.append((score, PlayCardAction(card=card)))
            elif card.card_type in ("SkipCard", "SeeTheFutureCard", "ShuffleCard", "NopeCard"):
                score = self._score_action(card, risk, defuse_count, hand_size, num_opponents)
                action_scores.append((score, PlayCardAction(card=card)))
            elif "Cat" in card.card_type:
                # Cat cards can be played alone (wastes them but avoids drawing)
                score = self._score_action(card, risk, defuse_count, hand_size, num_opponents)
                action_scores.append((score, PlayCardAction(card=card)))
        
        # Find best action
        if action_scores:
            action_scores.sort(key=lambda x: x[0], reverse=True)
            best_score, best_action = action_scores[0]
            
            # Decision: play if score > draw cost
            if best_score > draw_cost:
                return best_action
        
        # CRITICAL: Never draw with 0 Defuse if we have ANY card to play
        if defuse_count == 0 and action_scores:
            # Play any card rather than drawing
            return action_scores[0][1]
        
        # Default: draw
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Track game events for better decision making."""
        # Track opponent Defuse usage
        if event.event_type == EventType.EXPLODING_KITTEN_DEFUSED:
            player_id = event.player_id
            if player_id and player_id != view.my_id:
                self._opponent_defuse_used[player_id] = (
                    self._opponent_defuse_used.get(player_id, 0) + 1
                )
        
        # Track See the Future results
        if event.event_type == EventType.CARDS_PEEKED:
            if event.player_id == view.my_id:
                event_data: dict[str, Any] = event.data or {{}}
                card_types: Any = event_data.get("card_types", [])
                if isinstance(card_types, list):
                    self._last_peek = []
                    for ct in card_types:  # type: ignore
                        self._last_peek.append(str(ct))  # type: ignore
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """
        React to opponent actions with Nope cards.
        
        Only Nope things that directly threaten us.
        """
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        if not nope_cards:
            return None
        
        event_data = triggering_event.data or {{}}
        
        # Always Nope Attacks (they force us to draw twice)
        if event_data.get("card_type") == "AttackCard":
            return PlayCardAction(card=nope_cards[0])
        
        # Nope Favors targeting us
        if triggering_event.event_type == EventType.FAVOR_REQUESTED:
            target = event_data.get("target_player_id")
            if target == view.my_id:
                return PlayCardAction(card=nope_cards[0])
        
        # Nope Combos targeting us
        if triggering_event.event_type == EventType.COMBO_PLAYED:
            target = event_data.get("target_player_id")
            if target == view.my_id:
                return PlayCardAction(card=nope_cards[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        Choose where to place Exploding Kitten after defusing.
        
        Strategy: Place it as close to the top as possible to hit opponents.
        """
        num_opponents = len(view.other_players)
        
        if num_opponents == 1:
            # Endgame: put it on top (position 0)
            return 0
        elif num_opponents == 2:
            # Semi-final: position 1
            return min(1, draw_pile_size)
        else:
            # Early game: position 2
            return min(2, draw_pile_size)
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """
        Choose which card to give when targeted by Favor.
        
        Never give Defuse or Nope if possible.
        """
        hand = list(view.my_hand)
        
        # Filter out valuable cards
        safe_to_give = [
            c for c in hand
            if c.card_type not in ("DefuseCard", "NopeCard")
        ]
        
        if not safe_to_give:
            # Must give something valuable
            return hand[0]
        
        # Sort by value (give least valuable first)
        safe_to_give.sort(key=lambda c: (
            0 if "Cat" in c.card_type else
            1 if c.card_type == "ShuffleCard" else
            2 if c.card_type == "SeeTheFutureCard" else
            3 if c.card_type == "SkipCard" else
            4 if c.card_type == "FavorCard" else
            5 if c.card_type == "AttackCard" else
            6
        ))
        
        return safe_to_give[0]
    
    def on_explode(self, view: BotView) -> None:
        """Last words when eliminated."""
        view.say("The mission continues...")
'''


def format_weights_dict(weights: dict[str, float]) -> str:
    """Format weights dictionary as a clean Python dict string."""
    lines = ["{"]
    for key, value in weights.items():
        lines.append(f'    "{key}": {value:.6f},')
    lines.append("}")
    return "\n".join(lines)


def rewrite_bot_file(weights: dict[str, float]) -> None:
    """
    Rewrite the bot file with new weights.
    
    Args:
        weights: New weight dictionary to write.
    """
    bot_file = parent_dir / "bots" / "mossad_bot_advanced.py"
    weights_str = format_weights_dict(weights)
    content = BOT_FILE_TEMPLATE.format(weights_str=weights_str)
    bot_file.write_text(content)


# ============================================================================
# HILL CLIMBING ALGORITHM
# ============================================================================

def run_hill_climber(
    target_win_rate: float = 0.55,
    max_generations: int = 20,
    games_per_test: int = 50,
    log_file: str = "hill_climber_log.json",
) -> dict[str, float]:
    """
    Run the Steepest Ascent Hill Climbing algorithm.
    
    Args:
        target_win_rate: Stop when this win rate is achieved.
        max_generations: Maximum number of generations to run.
        games_per_test: Number of games per fitness test.
        log_file: Path to save training log.
    
    Returns:
        The best weights found.
    """
    # Import initial weights
    from bots.mossad_bot_advanced import DEFAULT_WEIGHTS
    
    print("=" * 70)
    print("🧬 HILL CLIMBER TRAINING SYSTEM")
    print("=" * 70)
    print(f"🎯 Target Win Rate: {target_win_rate:.0%}")
    print(f"🔄 Max Generations: {max_generations}")
    print(f"🎮 Games per Test: {games_per_test}")
    print("=" * 70)
    print()
    
    # Initialize
    current_weights = copy.deepcopy(DEFAULT_WEIGHTS)
    simulator = GameSimulator()
    training_log: list[dict[str, Any]] = []
    
    # Baseline test
    print("📊 Testing Baseline", end="")
    baseline_win_rate = simulator.run_batch(current_weights, games_per_test)
    print(f"   Win Rate: {baseline_win_rate:.1%}")
    print(f"   Weights: {current_weights}")
    print()
    
    training_log.append({
        "generation": 0,
        "type": "baseline",
        "win_rate": baseline_win_rate,
        "weights": copy.deepcopy(current_weights),
    })
    
    best_win_rate = baseline_win_rate
    
    # Main loop
    for generation in range(1, max_generations + 1):
        print(f"{'='*70}")
        print(f"🧬 Generation {generation}/{max_generations}")
        print(f"{'='*70}")
        print(f"📈 Current Best: {best_win_rate:.1%}")
        print()
        
        # Test baseline with current weights
        print("📊 Testing Current", end="")
        current_win_rate = simulator.run_batch(current_weights, games_per_test)
        print(f"   Win Rate: {current_win_rate:.1%}")
        
        # Generate and test mutations
        mutation_results: list[tuple[str, dict[str, float], float]] = []
        
        for strategy_name, mutate_fn in MUTATION_STRATEGIES:
            mutated_weights = mutate_fn(current_weights)
            print(f"   {strategy_name}", end="")
            win_rate = simulator.run_batch(mutated_weights, games_per_test)
            print(f"   Win Rate: {win_rate:.1%}")
            mutation_results.append((strategy_name, mutated_weights, win_rate))
        
        # Find the best mutation
        mutation_results.sort(key=lambda x: x[2], reverse=True)
        best_mutation_name, best_mutation_weights, best_mutation_rate = mutation_results[0]
        
        print()
        print(f"🏅 Best Mutation: {best_mutation_name} ({best_mutation_rate:.1%})")
        
        # Selection: Is the best mutation better than current?
        if best_mutation_rate > current_win_rate:
            print(f"🏆 Improvement Found! {current_win_rate:.1%} -> {best_mutation_rate:.1%}")
            current_weights = best_mutation_weights
            best_win_rate = best_mutation_rate
            
            # Rewrite bot file with new weights
            rewrite_bot_file(current_weights)
            print("📝 Updated bot file with new weights")
            
            training_log.append({
                "generation": generation,
                "type": "improvement",
                "strategy": best_mutation_name,
                "win_rate": best_mutation_rate,
                "weights": copy.deepcopy(current_weights),
            })
        else:
            print(f"📉 No improvement. Keeping current ({current_win_rate:.1%})")
            
            training_log.append({
                "generation": generation,
                "type": "no_improvement",
                "best_mutation": best_mutation_name,
                "mutation_rate": best_mutation_rate,
                "current_rate": current_win_rate,
            })
        
        print()
        
        # Check if target achieved
        if best_win_rate >= target_win_rate:
            print("=" * 70)
            print(f"🎉 TARGET ACHIEVED! Win Rate: {best_win_rate:.1%}")
            print("=" * 70)
            break
        
        # Save log periodically
        if generation % 5 == 0:
            log_path = Path(__file__).parent / log_file
            log_path.write_text(json.dumps(training_log, indent=2))
            print(f"💾 Log saved to {log_file}")
            print()
    
    # Final summary
    print()
    print("=" * 70)
    print("🏁 TRAINING COMPLETE")
    print("=" * 70)
    print(f"🎯 Final Win Rate: {best_win_rate:.1%}")
    print(f"🎯 Target: {target_win_rate:.1%}")
    print(f"📊 Final Weights:")
    for key, value in current_weights.items():
        print(f"   {key}: {value:.4f}")
    
    if best_win_rate >= target_win_rate:
        print()
        print("✅ SUCCESS! Target win rate achieved!")
    else:
        print()
        print("⚠️ Target not reached. Consider running more generations.")
    
    # Save final log
    log_path = Path(__file__).parent / log_file
    training_log.append({
        "type": "final",
        "win_rate": best_win_rate,
        "weights": copy.deepcopy(current_weights),
    })
    log_path.write_text(json.dumps(training_log, indent=2))
    print(f"\n💾 Training log saved to {log_path}")
    
    return current_weights


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hill Climber Training System for MossadBotAdvanced"
    )
    parser.add_argument(
        "--target-win-rate",
        type=float,
        default=0.55,
        help="Target win rate to achieve (default: 0.55 = 55%%)",
    )
    parser.add_argument(
        "--max-generations",
        type=int,
        default=20,
        help="Maximum number of generations (default: 20)",
    )
    parser.add_argument(
        "--games-per-test",
        type=int,
        default=50,
        help="Number of games per fitness test (default: 50)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="hill_climber_log.json",
        help="Path to training log file (default: hill_climber_log.json)",
    )
    
    args = parser.parse_args()
    
    run_hill_climber(
        target_win_rate=args.target_win_rate,
        max_generations=args.max_generations,
        games_per_test=args.games_per_test,
        log_file=args.log_file,
    )


if __name__ == "__main__":
    main()
