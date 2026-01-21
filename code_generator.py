"""
Code Generator - Generate bot improvements for 5-player battle royale.
"""

import random
from pathlib import Path
from typing import Any


class CodeGenerator:
    """Generate code improvements for the bot using dynamic parameter tuning."""
    
    def __init__(self) -> None:
        """Initialize code generator with tunable parameters."""
        # Initial Parameters (These will evolve)
        self.params: dict[str, Any] = {
            "crowd_panic_threshold": 1,  # If players > 2, panic if defuse <= this
            "duel_panic_threshold": 0,   # If players == 2, panic if defuse <= this
            "aggression_bias": 0.3,      # Probability to attack aggressively
            "hoard_pairs": True,         # Keep pairs for stealing
            "combo_priority": 1.5,        # Priority multiplier for combos
            "skip_priority": 1.0,        # Priority multiplier for Skip cards
        }
        self.iteration_count = 0
        self.bot_file = Path("bots/mossad_bot.py")
    
    def generate_improvements(
        self, analysis: dict[str, Any], win_rate: float
    ) -> list[str]:
        """Adjusts parameters based on failure analysis and rewrites bot."""
        self.iteration_count += 1
        
        changes: list[str] = []
        
        # LOGIC TUNING
        
        # 1. Dying early (4th/5th place)? Be more paranoid in Crowd Mode.
        rate_early_death = analysis.get("rate_early_death", 0.0)
        if rate_early_death > 0.3:
            if self.params["crowd_panic_threshold"] < 2:
                self.params["crowd_panic_threshold"] = 2
                changes.append("Increased Crowd Panic (Safety First)")
            elif self.params["crowd_panic_threshold"] < 3:
                self.params["crowd_panic_threshold"] = 3
                changes.append("Increased Crowd Panic to 3")
        
        # 2. Dying with full hands? Stop hoarding, use cards!
        rate_hoarding_death = analysis.get("rate_hoarding_death", 0.0)
        if rate_hoarding_death > 0.2:
            self.params["aggression_bias"] = min(0.8, self.params["aggression_bias"] + 0.2)
            self.params["hoard_pairs"] = False
            changes.append("Increased Aggression (Use cards!)")
        
        # 3. Dying without defuse? Increase panic thresholds
        rate_starvation = analysis.get("rate_starvation", 0.0)
        if rate_starvation > 0.4:
            self.params["crowd_panic_threshold"] = max(
                self.params["crowd_panic_threshold"],
                min(3, self.params["crowd_panic_threshold"] + 1)
            )
            self.params["duel_panic_threshold"] = max(
                self.params["duel_panic_threshold"],
                min(2, self.params["duel_panic_threshold"] + 1)
            )
            changes.append("Increased Panic Thresholds (Defuse Starvation)")
        
        # 4. Dying late (2nd/3rd)? We're close! Increase combo priority
        rate_late_death = analysis.get("rate_late_death", 0.0)
        if rate_late_death > 0.3:
            self.params["combo_priority"] = min(2.5, self.params.get("combo_priority", 1.5) * 1.2)
            self.params["hoard_pairs"] = False  # Use pairs to win!
            changes.append("Increased Combo Priority (Close to Winning!)")
        
        # 5. Random Mutation if stuck
        if not changes and win_rate < 0.30:
            if random.random() > 0.5:
                self.params["aggression_bias"] = random.uniform(0.2, 0.8)
                changes.append(f"Randomized Aggression to {self.params['aggression_bias']:.2f}")
            else:
                self.params["hoard_pairs"] = not self.params["hoard_pairs"]
                changes.append("Flipped Hoarding Strategy")
        
        # Apply changes to bot file
        self._write_bot_file()
        
        return changes if changes else ["No changes"]
    
    def _write_bot_file(self) -> None:
        """Write bot file with current parameters."""
        code = f'''"""
Auto-Optimized Bot for 5-Player Battle Royale (Iteration {self.iteration_count})
Parameters: {self.params}
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


class MossadBot(Bot):
    """
    Auto-Optimized Bot for 5-Player Battle Royale.
    
    Strategy:
    - Crowd Mode (3+ players): Conservative, avoid drawing
    - Duel Mode (2 players): Aggressive, steal Defuse
    """
    
    def __init__(self) -> None:
        """Initialize with tracking."""
        self._last_peek: list[str] = []
        self._opponent_defuse_used: dict[str, int] = {{}}
        
    @property
    def name(self) -> str:
        """Return the bot's display name."""
        return "MossadBot"
    
    def _count_defuse(self, hand: tuple[Card, ...]) -> int:
        """Count Defuse cards in hand."""
        return sum(1 for c in hand if c.card_type == "DefuseCard")
    
    def _find_three_of_kind(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        """Find three-of-a-kind combo."""
        combo_cards = [c for c in hand if c.can_combo()]
        if not combo_cards:
            return None
        
        by_type: dict[str, list[Card]] = {{}}
        for card in combo_cards:
            if card.card_type not in by_type:
                by_type[card.card_type] = []
            by_type[card.card_type].append(card)
        
        for cards in by_type.values():
            if len(cards) >= 3:
                return tuple(cards[:3])
        
        return None
    
    def _find_two_of_kind(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        """Find two-of-a-kind combo."""
        combo_cards = [c for c in hand if c.can_combo()]
        if not combo_cards:
            return None
        
        by_type: dict[str, list[Card]] = {{}}
        for card in combo_cards:
            if card.card_type not in by_type:
                by_type[card.card_type] = []
            by_type[card.card_type].append(card)
        
        for cards in by_type.values():
            if len(cards) >= 2:
                return tuple(cards[:2])
        
        return None
    
    def take_turn(self, view: BotView) -> Action:
        """
        Parameterized turn strategy for 5-player battle royale.
        """
        hand = view.my_hand
        defuse_count = self._count_defuse(hand)
        draw_pile_size = view.draw_pile_count
        
        # Determine game phase (Crowd Mode vs Duel Mode)
        num_opponents = len(view.other_players)
        is_duel = num_opponents == 1  # Only 1 opponent = duel mode
        is_crowd = num_opponents >= 3  # 3+ opponents = crowd mode
        
        # Parameters
        PANIC_LEVEL = {self.params["duel_panic_threshold"]} if is_duel else {self.params["crowd_panic_threshold"]}
        AGGRESSION = {self.params["aggression_bias"]}
        HOARD_PAIRS = {self.params["hoard_pairs"]}
        COMBO_PRIORITY = {self.params.get("combo_priority", 1.5)}
        
        # Get card types
        skip_cards = [c for c in hand if c.card_type == "SkipCard"]
        attack_cards = [c for c in hand if c.card_type == "AttackCard"]
        shuffle_cards = [c for c in hand if c.card_type == "ShuffleCard"]
        see_future_cards = [c for c in hand if c.card_type == "SeeTheFutureCard"]
        nope_cards = [c for c in hand if c.card_type == "NopeCard"]
        favor_cards = [c for c in hand if c.card_type == "FavorCard"]
        cat_cards = [c for c in hand if "Cat" in c.card_type]
        
        # PRIORITY 1: CRITICAL SURVIVAL - If defuse count is low, play safety cards
        if defuse_count <= PANIC_LEVEL:
            # Play ANYTHING that skips a turn or avoids drawing
            if attack_cards and view.other_players:
                return PlayCardAction(card=attack_cards[0])
            if skip_cards:
                return PlayCardAction(card=skip_cards[0])
            if see_future_cards and is_duel:  # Only use See Future in duel to snipe
                return PlayCardAction(card=see_future_cards[0])
            if shuffle_cards:
                return PlayCardAction(card=shuffle_cards[0])
            if nope_cards:
                return PlayCardAction(card=nope_cards[0])
            if cat_cards:
                return PlayCardAction(card=cat_cards[0])
        
        # PRIORITY 2: STEALING (The only way to win 1v1)
        # If we have pairs, steal! (Especially in duel mode)
        if COMBO_PRIORITY >= 1.0:
            three_combo = self._find_three_of_kind(hand)
            if three_combo and view.other_players:
                return PlayComboAction(cards=three_combo, target_player_id=view.other_players[0])
            
            two_combo = self._find_two_of_kind(hand)
            if two_combo and view.other_players:
                # In duel mode or if not hoarding, play combos
                if is_duel or not HOARD_PAIRS:
                    return PlayComboAction(cards=two_combo, target_player_id=view.other_players[0])
        
        # PRIORITY 3: AGGRESSION / DUMPING
        # If RNG says attack or we have too many cards, use them!
        import random
        if random.random() < AGGRESSION:
            if attack_cards and view.other_players:
                return PlayCardAction(card=attack_cards[0])
        
        if len(hand) > 5:
            # Dump cards to avoid explosion risk
            if attack_cards and view.other_players:
                return PlayCardAction(card=attack_cards[0])
            if skip_cards:
                return PlayCardAction(card=skip_cards[0])
            if cat_cards:
                return PlayCardAction(card=cat_cards[0])
        
        # PRIORITY 4: Favor cards (might get Defuse)
        if favor_cards and view.other_players:
            return PlayCardAction(card=favor_cards[0], target_player_id=view.other_players[0])
        
        # Default: Draw (only if we have Defuse protection)
        if defuse_count >= 1:
            return DrawCardAction()
        
        # Last resort: play any card to avoid drawing
        if nope_cards:
            return PlayCardAction(card=nope_cards[0])
        if cat_cards:
            return PlayCardAction(card=cat_cards[0])
        
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Track opponent Defuse usage and See the Future results."""
        if event.event_type == EventType.EXPLODING_KITTEN_DEFUSED:
            player_id = event.player_id
            if player_id and player_id != view.my_id:
                self._opponent_defuse_used[player_id] = (
                    self._opponent_defuse_used.get(player_id, 0) + 1
                )
        
        if event.event_type == EventType.CARDS_PEEKED:
            if event.player_id == view.my_id:
                event_data: dict[str, Any] = event.data or {{}}
                card_types: Any = event_data.get("card_types", [])
                if isinstance(card_types, list):
                    self._last_peek = []
                    for ct in card_types:  # type: ignore
                        self._last_peek.append(str(ct))  # type: ignore
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """Nope Attacks, Favors, and Combos targeting us."""
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        if not nope_cards:
            return None
        
        event_type = triggering_event.event_type
        event_data = triggering_event.data or {{}}
        
        if event_data.get("card_type") == "AttackCard":
            return PlayCardAction(card=nope_cards[0])
        
        if event_type == EventType.FAVOR_REQUESTED:
            target = event_data.get("target_player_id")
            if target == view.my_id:
                return PlayCardAction(card=nope_cards[0])
        
        if event_type == EventType.COMBO_PLAYED:
            target = event_data.get("target_player_id")
            if target == view.my_id:
                return PlayCardAction(card=nope_cards[0])
        
        return None
    
    def choose_defuse_position(
        self, view: BotView, draw_pile_size: int
    ) -> int:
        """Place Exploding Kitten strategically."""
        num_opponents = len(view.other_players)
        if num_opponents == 1:
            return 0  # Endgame: maximum aggression
        elif num_opponents == 2:
            return min(1, draw_pile_size)
        else:
            return min(2, draw_pile_size)
    
    def choose_card_to_give(
        self, view: BotView, requester_id: str
    ) -> Card:
        """Give least valuable card."""
        hand = list(view.my_hand)
        safe_to_give = [
            c for c in hand
            if c.card_type not in ("DefuseCard", "NopeCard")
        ]
        
        if not safe_to_give:
            return hand[0]
        
        safe_to_give.sort(key=lambda c: (
            0 if "Cat" in c.card_type else
            1 if c.card_type == "SkipCard" else
            2 if c.card_type == "ShuffleCard" else
            3 if c.card_type == "SeeTheFutureCard" else
            4 if c.card_type == "FavorCard" else
            5 if c.card_type == "AttackCard" else
            6
        ))
        
        return safe_to_give[0]
    
    def on_explode(self, view: BotView) -> None:
        """Last words."""
        view.say("Mission failed. We'll get them next time.")
'''
        
        # Write to file
        self.bot_file.write_text(code)
