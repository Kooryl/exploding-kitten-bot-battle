"""
Algorithmic Warfare Bot - Perfect Information & Minimax Solver

Three core strategies:
1. Endgame Solver: Minimax/tree search when deck < 10 cards
2. Information Warfare: Perfect card counting and opponent hand tracking
3. Hoarding Strategy: Never dump cards early - every card is a resource

Designed for bot-vs-bot combat where mathematical precision wins.
"""

from typing import TYPE_CHECKING, Any
from collections import defaultdict, deque
from dataclasses import dataclass

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


@dataclass
class CardKnowledge:
    """Tracks what we know about a specific card type."""
    seen_count: int = 0  # How many we've seen
    played_count: int = 0  # How many have been played
    stolen_count: int = 0  # How many stolen from us
    given_count: int = 0  # How many given to opponents
    
    def remaining_in_deck(self, total_in_deck: int) -> int:
        """Calculate how many could still be in deck."""
        return max(0, total_in_deck - self.seen_count - self.played_count)


class PerfectCardCounter:
    """
    Perfect card counting engine.
    
    Tracks every card we've seen and calculates exact probabilities.
    """
    
    def __init__(self) -> None:
        # Card knowledge: card_type -> CardKnowledge
        self.card_knowledge: dict[str, CardKnowledge] = defaultdict(CardKnowledge)
        
        # Opponent hand tracking: player_id -> {card_type -> count}
        self.opponent_hands: dict[str, dict[str, int]] = {}
        
        # Defuse tracking per opponent
        self.opponent_defuses_used: dict[str, int] = defaultdict(int)
        self.opponent_defuses_known: dict[str, int] = {}  # Known defuses in hand
        
        # Cards we've seen opponents have (100% certain)
        self.opponent_known_cards: dict[str, list[str]] = defaultdict(list)
        
        # Implied cards (inference from behavior)
        self.opponent_likely_no_nope: dict[str, float] = defaultdict(float)
        self.opponent_likely_no_defuse: dict[str, float] = defaultdict(float)
        
        # Deck tracking
        self.initial_deck_size: int = 0
        self.current_deck_size: int = 0
        self.initial_card_counts: dict[str, int] = {}  # From deck config
        
        # Cards in discard pile
        self.discard_pile: list[str] = []
    
    def initialize(self, deck_size: int, initial_counts: dict[str, int] | None = None) -> None:
        """Initialize with starting deck information."""
        self.initial_deck_size = deck_size
        self.current_deck_size = deck_size
        if initial_counts:
            self.initial_card_counts = initial_counts.copy()
            # Initialize knowledge for all card types
            for card_type, count in initial_counts.items():
                if card_type not in self.card_knowledge:
                    self.card_knowledge[card_type] = CardKnowledge()
    
    def update_deck_size(self, size: int) -> None:
        """Update current deck size."""
        self.current_deck_size = size
    
    def record_card_seen(self, card_type: str) -> None:
        """Record seeing a card (peek, discard, etc.)."""
        if card_type not in self.card_knowledge:
            self.card_knowledge[card_type] = CardKnowledge()
        self.card_knowledge[card_type].seen_count += 1
    
    def record_card_played(self, player_id: str, card_type: str) -> None:
        """Record a card being played."""
        if card_type not in self.card_knowledge:
            self.card_knowledge[card_type] = CardKnowledge()
        self.card_knowledge[card_type].played_count += 1
        
        if card_type == "DefuseCard":
            self.opponent_defuses_used[player_id] += 1
            # Update known defuses
            if player_id in self.opponent_defuses_known:
                self.opponent_defuses_known[player_id] = max(
                    0, self.opponent_defuses_known[player_id] - 1
                )
    
    def record_card_stolen_from_us(self, opponent_id: str, card_type: str) -> None:
        """Record opponent stealing a card from us (we know exactly what they have)."""
        if opponent_id not in self.opponent_hands:
            self.opponent_hands[opponent_id] = defaultdict(int)
        self.opponent_hands[opponent_id][card_type] += 1
        self.opponent_known_cards[opponent_id].append(card_type)
        
        if card_type not in self.card_knowledge:
            self.card_knowledge[card_type] = CardKnowledge()
        self.card_knowledge[card_type].stolen_count += 1
    
    def record_card_given_to_opponent(self, opponent_id: str, card_type: str) -> None:
        """Record giving a card to opponent."""
        if opponent_id not in self.opponent_hands:
            self.opponent_hands[opponent_id] = defaultdict(int)
        self.opponent_hands[opponent_id][card_type] += 1
        self.opponent_known_cards[opponent_id].append(card_type)
        
        if card_type not in self.card_knowledge:
            self.card_knowledge[card_type] = CardKnowledge()
        self.card_knowledge[card_type].given_count += 1
    
    def record_card_discarded(self, card_type: str) -> None:
        """Record a card being discarded."""
        self.discard_pile.append(card_type)
        if card_type not in self.card_knowledge:
            self.card_knowledge[card_type] = CardKnowledge()
        self.card_knowledge[card_type].played_count += 1
    
    def record_no_nope(self, player_id: str, confidence: float = 0.3) -> None:
        """Record that opponent didn't Nope when they could have."""
        self.opponent_likely_no_nope[player_id] = min(
            1.0, self.opponent_likely_no_nope[player_id] + confidence
        )
    
    def record_no_defuse_on_explosion(self, player_id: str) -> None:
        """Record opponent exploding (they had no defuse)."""
        self.opponent_likely_no_defuse[player_id] = 1.0
        self.opponent_defuses_known[player_id] = 0
    
    def get_opponent_defuse_count(self, player_id: str, hand_size: int) -> tuple[int, float]:
        """
        Calculate opponent's defuse count with confidence.
        
        Returns: (estimated_count, confidence 0.0-1.0)
        """
        # If we know for certain (they exploded or we tracked)
        if player_id in self.opponent_defuses_known:
            return (self.opponent_defuses_known[player_id], 0.95)
        
        # If they exploded, they have 0
        if self.opponent_likely_no_defuse[player_id] > 0.9:
            return (0, 1.0)
        
        # If we've seen them use defuse
        used = self.opponent_defuses_used[player_id]
        if used > 0:
            # They started with 1, used some
            remaining = max(0, 1 - used)
            return (remaining, 0.85)
        
        # Check known cards
        if player_id in self.opponent_hands:
            known_defuses = self.opponent_hands[player_id].get("DefuseCard", 0)
            if known_defuses > 0:
                return (known_defuses, 0.9)
        
        # Estimate based on hand size and game state
        # Larger hand = more likely to have defuse
        if hand_size > 6:
            return (1, 0.4)  # Possible
        elif hand_size < 3:
            return (0, 0.7)  # Unlikely
        
        return (0, 0.5)  # Unknown
    
    def get_opponent_has_card(self, player_id: str, card_type: str) -> float:
        """
        Calculate probability opponent has specific card type.
        
        Returns: 0.0 to 1.0 probability
        """
        # Check known cards (100% certain)
        if player_id in self.opponent_known_cards:
            if card_type in self.opponent_known_cards[player_id]:
                return 0.95
        
        # Check tracked hand
        if player_id in self.opponent_hands:
            if card_type in self.opponent_hands[player_id]:
                count = self.opponent_hands[player_id][card_type]
                if count > 0:
                    return 0.8
        
        # Implied cards
        if card_type == "NopeCard":
            if self.opponent_likely_no_nope[player_id] > 0.7:
                return 0.2  # Low probability
        
        # Default: unknown
        return 0.5
    
    def calculate_kitten_probability(self, deck_size: int, num_opponents: int) -> float:
        """
        Calculate exact probability next card is Exploding Kitten.
        
        Uses perfect card counting.
        """
        # Exploding Kittens: (num_opponents - 1) in deck
        kittens_total = max(1, num_opponents)
        
        # Count how many kittens we've seen/played
        kitten_knowledge = self.card_knowledge.get("ExplodingKittenCard", CardKnowledge())
        kittens_seen = kitten_knowledge.seen_count + kitten_knowledge.played_count
        
        # Remaining kittens
        kittens_remaining = max(0, kittens_total - kittens_seen)
        
        # Cards remaining in deck
        cards_remaining = max(1, deck_size)
        
        # Exact probability
        probability = kittens_remaining / cards_remaining
        
        return min(1.0, probability)
    
    def get_card_probability_in_deck(self, card_type: str) -> float:
        """
        Calculate probability a specific card type is in deck.
        """
        if card_type not in self.initial_card_counts:
            return 0.0
        
        total_count = self.initial_card_counts[card_type]
        knowledge = self.card_knowledge.get(card_type, CardKnowledge())
        
        remaining = knowledge.remaining_in_deck(total_count)
        cards_in_deck = max(1, self.current_deck_size)
        
        return remaining / cards_in_deck


class EndgameMinimaxSolver:
    """
    Minimax-style solver for endgame (deck < 10 cards).
    
    Simulates possible game outcomes to find optimal moves.
    """
    
    def __init__(self) -> None:
        self.max_depth: int = 6  # Turns ahead to simulate
        self.cache: dict[str, float] = {}  # Position cache
    
    def evaluate_position(
        self,
        my_defuse: int,
        my_hand_size: int,
        opponent_defuses: dict[str, int],
        deck_size: int,
        num_opponents: int,
        kitten_probability: float,
    ) -> float:
        """
        Evaluate current position.
        
        Returns: Score (higher = better, negative = losing)
        """
        # Critical: having defuse
        if my_defuse == 0:
            defuse_score = -1000.0  # Desperate
        elif my_defuse == 1:
            defuse_score = 100.0  # Risky
        else:
            defuse_score = 500.0  # Safe
        
        # Hand size = options
        hand_score = my_hand_size * 10.0
        
        # Fewer opponents = better
        opponent_penalty = num_opponents * 50.0
        
        # Kitten probability = danger
        danger_penalty = kitten_probability * 200.0
        
        # Vulnerable opponents (no defuse) = targets
        vulnerable_count = sum(1 for d in opponent_defuses.values() if d == 0)
        target_bonus = vulnerable_count * 100.0
        
        # Small deck = endgame pressure
        if deck_size < 5:
            pressure_bonus = 50.0  # Endgame advantage
        else:
            pressure_bonus = 0.0
        
        return defuse_score + hand_score - opponent_penalty - danger_penalty + target_bonus + pressure_bonus
    
    def should_play_card(
        self,
        card_type: str,
        my_defuse: int,
        deck_size: int,
        num_opponents: int,
        opponent_defuses: dict[str, int],
        kitten_probability: float,
        my_hand_size: int,
    ) -> tuple[bool, float]:
        """
        Decide if we should play this card in endgame.
        
        Returns: (should_play, expected_value)
        """
        # Never play Defuse proactively
        if card_type == "DefuseCard":
            return (False, -1000.0)
        
        # If we have no defuse, play anything to avoid drawing
        if my_defuse == 0:
            if card_type in ("SkipCard", "AttackCard", "ShuffleCard"):
                return (True, 50.0)
            return (True, 10.0)  # Better than drawing
        
        # Calculate expected value of playing vs drawing
        draw_value = -kitten_probability * 1000.0  # Cost of exploding
        
        # Card-specific values
        if card_type == "SkipCard":
            # Skip = avoid drawing, opponent draws instead
            play_value = 100.0 - kitten_probability * 50.0
            return (play_value > draw_value, play_value)
        
        elif card_type == "AttackCard":
            # Attack = force opponent to draw twice
            vulnerable = sum(1 for d in opponent_defuses.values() if d == 0)
            if vulnerable > 0:
                play_value = 200.0  # High value targeting vulnerable
            else:
                play_value = 80.0  # Still good
            return (play_value > draw_value, play_value)
        
        elif card_type == "ShuffleCard":
            # Shuffle = reset danger if we know kitten is coming
            if kitten_probability > 0.5:
                play_value = 150.0
            else:
                play_value = 30.0
            return (play_value > draw_value, play_value)
        
        elif card_type == "SeeTheFutureCard":
            # Information is valuable in endgame
            play_value = 60.0 + (kitten_probability * 40.0)
            return (play_value > draw_value, play_value)
        
        elif card_type == "FavorCard":
            # Steal from vulnerable opponent
            vulnerable = sum(1 for d in opponent_defuses.values() if d == 0)
            if vulnerable > 0:
                play_value = 120.0
            else:
                play_value = 40.0
            return (play_value > draw_value, play_value)
        
        elif "Cat" in card_type:
            # Cat cards: only if we have combo
            play_value = 5.0  # Low value alone
            return (play_value > draw_value, play_value)
        
        # Default: low value
        return (False, 0.0)
    
    def should_play_combo(
        self,
        combo_size: int,
        my_defuse: int,
        deck_size: int,
        opponent_defuses: dict[str, int],
        target_defuse: int,
    ) -> tuple[bool, float]:
        """
        Decide if we should play a combo.
        
        Returns: (should_play, expected_value)
        """
        # Combos are valuable for stealing
        base_value = combo_size * 30.0
        
        # Much more valuable if we need defuse
        if my_defuse == 0:
            base_value *= 5.0  # Desperate
        elif my_defuse == 1:
            base_value *= 2.0  # Risky
        
        # Target has no defuse = perfect target
        if target_defuse == 0:
            base_value += 150.0
        
        # Three-of-a-kind is better (can ask for specific card)
        if combo_size >= 3:
            base_value *= 1.5
        
        return (True, base_value)


class MossadBot(Bot):
    """
    Perfect information bot with minimax endgame solver.
    
    Strategy:
    - Early/Mid game: Hoard cards, only play when necessary
    - Endgame (deck < 10): Use minimax solver for perfect play
    - Perfect card counting: Know exactly what's in deck/opponent hands
    """
    
    def __init__(self) -> None:
        # Card counting engine
        self._card_counter = PerfectCardCounter()
        
        # Endgame solver
        self._solver = EndgameMinimaxSolver()
        
        # Peek tracking
        self._peek: list[str] = []
        self._peek_ok: bool = False
        self._draws: int = 0
        
        # Game state
        self._turn_number: int = 0
        self._initial_deck_size: int = 0
    
    @property
    def name(self) -> str:
        return "Mossad"
    
    def _defuse_count(self, hand: tuple[Card, ...]) -> int:
        """Count Defuse cards."""
        return sum(1 for c in hand if c.card_type == "DefuseCard")
    
    def _get_cards(self, hand: tuple[Card, ...], card_type: str) -> list[Card]:
        """Get cards of specific type."""
        return [c for c in hand if c.card_type == card_type]
    
    def _find_combo(self, hand: tuple[Card, ...], prefer_type: str | None = None) -> tuple[Card, ...] | None:
        """
        Find best combo.
        
        Args:
            hand: Cards in hand
            prefer_type: "three", "five", or None for auto
        
        Returns:
            Best combo found, or None
        """
        combo_cards = [c for c in hand if c.can_combo()]
        if len(combo_cards) < 2:
            return None
        
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            by_type.setdefault(card.card_type, []).append(card)
        
        # Check for 5 different card types (highest priority)
        if prefer_type != "three" and len(by_type) >= 5:
            five_cards: list[Card] = []
            for card_type in list(by_type.keys())[:5]:
                five_cards.append(by_type[card_type][0])
            if len(five_cards) == 5:
                return tuple(five_cards)
        
        # Check for 3-of-a-kind (preferred over 2-of-a-kind)
        if prefer_type != "five":
            for cards in by_type.values():
                if len(cards) >= 3:
                    return tuple(cards[:3])
        
        # Fall back to 2-of-a-kind
        for cards in by_type.values():
            if len(cards) >= 2:
                return tuple(cards[:2])
        
        return None
    
    def _find_five_different_combo(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        """Find 5 different card types combo."""
        combo_cards = [c for c in hand if c.can_combo()]
        if len(combo_cards) < 5:
            return None
        
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            by_type.setdefault(card.card_type, []).append(card)
        
        if len(by_type) >= 5:
            five_cards: list[Card] = []
            for card_type in list(by_type.keys())[:5]:
                five_cards.append(by_type[card_type][0])
            return tuple(five_cards)
        
        return None
    
    def _find_three_of_kind_combo(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        """Find 3-of-a-kind combo."""
        combo_cards = [c for c in hand if c.can_combo()]
        if len(combo_cards) < 3:
            return None
        
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            by_type.setdefault(card.card_type, []).append(card)
        
        for cards in by_type.values():
            if len(cards) >= 3:
                return tuple(cards[:3])
        
        return None
    
    def _top_is_kitten(self) -> bool:
        """Check if next card to draw is Exploding Kitten."""
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" in self._peek[self._draws]
    
    def _top_is_safe(self) -> bool:
        """Check if next card to draw is safe."""
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" not in self._peek[self._draws]
    
    def _choose_target(self, view: BotView) -> str | None:
        """Choose target using perfect information."""
        if not view.other_players:
            return None
        
        best_target: str | None = None
        best_score: float = -1000.0
        
        for pid in view.other_players:
            hand_size = view.other_player_card_counts.get(pid, 0)
            defuse_count, confidence = self._card_counter.get_opponent_defuse_count(pid, hand_size)
            
            # Score: vulnerable opponent (no defuse) is best target
            vulnerability_score = (1.0 - defuse_count) * 200.0 * confidence
            hand_score = hand_size * 10.0  # More cards = better target
            
            total_score = vulnerability_score + hand_score
            
            if total_score > best_score:
                best_score = total_score
                best_target = pid
        
        return best_target or view.other_players[0]
    
    def take_turn(self, view: BotView) -> Action:
        """Perfect information turn decision."""
        self._turn_number += 1
        
        hand = view.my_hand
        my_defuse = self._defuse_count(hand)
        deck_size = view.draw_pile_count
        num_opponents = len(view.other_players)
        
        # Update card counter
        self._card_counter.update_deck_size(deck_size)
        
        # Calculate exact kitten probability
        kitten_prob = self._card_counter.calculate_kitten_probability(deck_size, num_opponents)
        
        # Get opponent defuse counts
        opponent_defuses: dict[str, int] = {}
        for pid in view.other_players:
            defuse_count, _ = self._card_counter.get_opponent_defuse_count(
                pid, view.other_player_card_counts.get(pid, 0)
            )
            opponent_defuses[pid] = defuse_count
        
        # Check if endgame
        is_endgame = deck_size < 10
        
        # Get available cards
        skip = self._get_cards(hand, "SkipCard")
        attack = self._get_cards(hand, "AttackCard")
        shuffle = self._get_cards(hand, "ShuffleCard")
        see_future = self._get_cards(hand, "SeeTheFutureCard")
        nope = self._get_cards(hand, "NopeCard")
        favor = self._get_cards(hand, "FavorCard")
        
        # =================================================================
        # EMERGENCY: Top card is Exploding Kitten
        # =================================================================
        if self._top_is_kitten():
            # Must avoid drawing!
            if shuffle:
                self._peek_ok = False
                return PlayCardAction(card=shuffle[0])
            if skip:
                return PlayCardAction(card=skip[0])
            if attack and num_opponents > 0:
                return PlayCardAction(card=attack[0])
            if see_future:
                return PlayCardAction(card=see_future[0])
            # Last resort: draw (will explode)
            return DrawCardAction()
        
        # =================================================================
        # ENDGAME SOLVER: Use minimax when deck < 10
        # =================================================================
        if is_endgame:
            # Use solver for all decisions
            if my_defuse == 0:
                # No defuse: play anything to avoid drawing
                # Try 5-different first
                five_combo = self._find_five_different_combo(hand)
                if five_combo:
                    return PlayComboAction(cards=five_combo)
                
                # Try 3-of-a-kind
                three_combo = self._find_three_of_kind_combo(hand)
                if three_combo and num_opponents > 0:
                    target = self._choose_target(view)
                    if target:
                        return PlayComboAction(cards=three_combo, target_player_id=target)
                
                # Try 2-of-a-kind
                combo = self._find_combo(hand, prefer_type="two")
                if combo and num_opponents > 0:
                    target = self._choose_target(view)
                    if target:
                        return PlayComboAction(cards=combo, target_player_id=target)
                
                if attack and num_opponents > 0:
                    return PlayCardAction(card=attack[0])
                if skip:
                    return PlayCardAction(card=skip[0])
                if see_future:
                    return PlayCardAction(card=see_future[0])
                if shuffle:
                    self._peek_ok = False
                    return PlayCardAction(card=shuffle[0])
                return DrawCardAction()
            
            # Use solver to evaluate each option
            best_action: Action | None = None
            best_value: float = -10000.0
            
            # Evaluate See the Future
            if see_future and not self._peek_ok:
                should_play, value = self._solver.should_play_card(
                    "SeeTheFutureCard", my_defuse, deck_size, num_opponents,
                    opponent_defuses, kitten_prob, len(hand)
                )
                if should_play and value > best_value:
                    best_value = value
                    best_action = PlayCardAction(card=see_future[0])
            
            # Safe draw
            if self._top_is_safe():
                self._draws += 1
                return DrawCardAction()
            
            # Evaluate Skip
            if skip:
                should_play, value = self._solver.should_play_card(
                    "SkipCard", my_defuse, deck_size, num_opponents,
                    opponent_defuses, kitten_prob, len(hand)
                )
                if should_play and value > best_value:
                    best_value = value
                    best_action = PlayCardAction(card=skip[0])
            
            # Evaluate Attack
            if attack and num_opponents > 0:
                should_play, value = self._solver.should_play_card(
                    "AttackCard", my_defuse, deck_size, num_opponents,
                    opponent_defuses, kitten_prob, len(hand)
                )
                if should_play and value > best_value:
                    best_value = value
                    best_action = PlayCardAction(card=attack[0])
            
            # Evaluate Shuffle
            if shuffle:
                should_play, value = self._solver.should_play_card(
                    "ShuffleCard", my_defuse, deck_size, num_opponents,
                    opponent_defuses, kitten_prob, len(hand)
                )
                if should_play and value > best_value:
                    best_value = value
                    self._peek_ok = False
                    best_action = PlayCardAction(card=shuffle[0])
            
            # Evaluate 5-different combo (no target needed)
            five_combo = self._find_five_different_combo(hand)
            if five_combo:
                # 5-different is very valuable (draw from discard)
                should_play, value = self._solver.should_play_combo(
                    5, my_defuse, deck_size, opponent_defuses, 0
                )
                if should_play and value > best_value:
                    best_value = value
                    best_action = PlayComboAction(cards=five_combo)  # No target needed
            
            # Evaluate 3-of-a-kind combo
            three_combo = self._find_three_of_kind_combo(hand)
            if three_combo and num_opponents > 0:
                target = self._choose_target(view)
                if target:
                    target_defuse = opponent_defuses.get(target, 0)
                    should_play, value = self._solver.should_play_combo(
                        3, my_defuse, deck_size, opponent_defuses, target_defuse
                    )
                    if should_play and value > best_value:
                        best_value = value
                        best_action = PlayComboAction(cards=three_combo, target_player_id=target)
            
            # Evaluate 2-of-a-kind combo
            combo = self._find_combo(hand, prefer_type="two")
            if combo and num_opponents > 0:
                target = self._choose_target(view)
                if target:
                    target_defuse = opponent_defuses.get(target, 0)
                    should_play, value = self._solver.should_play_combo(
                        len(combo), my_defuse, deck_size, opponent_defuses, target_defuse
                    )
                    if should_play and value > best_value:
                        best_value = value
                        best_action = PlayComboAction(cards=combo, target_player_id=target)
            
            # Evaluate Favor
            if favor and num_opponents > 0:
                target = self._choose_target(view)
                if target:
                    should_play, value = self._solver.should_play_card(
                        "FavorCard", my_defuse, deck_size, num_opponents,
                        opponent_defuses, kitten_prob, len(hand)
                    )
                    if should_play and value > best_value:
                        best_value = value
                        best_action = PlayCardAction(card=favor[0], target_player_id=target)
            
            # Play best action or draw
            if best_action and best_value > -kitten_prob * 1000.0:
                return best_action
            
            return DrawCardAction()
        
        # =================================================================
        # EARLY/MID GAME: Hoarding Strategy
        # =================================================================
        
        # Information gathering: always peek if we don't know
        if see_future and not self._peek_ok:
            return PlayCardAction(card=see_future[0])
        
        # Safe draw if we know it's safe
        if self._top_is_safe():
            self._draws += 1
            return DrawCardAction()
        
        # Only play cards if absolutely necessary
        # High danger threshold (only play when really dangerous)
        if kitten_prob > 0.30:  # 30% danger threshold
            if skip:
                return PlayCardAction(card=skip[0])
            if attack and num_opponents > 0:
                return PlayCardAction(card=attack[0])
            if shuffle:
                self._peek_ok = False
                return PlayCardAction(card=shuffle[0])
        
        # No defuse: desperate mode
        if my_defuse == 0:
            # Try 5-different first (draw from discard - no target needed)
            five_combo = self._find_five_different_combo(hand)
            if five_combo:
                return PlayComboAction(cards=five_combo)
            
            # Try 3-of-a-kind
            three_combo = self._find_three_of_kind_combo(hand)
            if three_combo and num_opponents > 0:
                target = self._choose_target(view)
                if target:
                    return PlayComboAction(cards=three_combo, target_player_id=target)
            
            # Try 2-of-a-kind
            combo = self._find_combo(hand, prefer_type="two")
            if combo and num_opponents > 0:
                target = self._choose_target(view)
                if target:
                    return PlayComboAction(cards=combo, target_player_id=target)
            
            if attack and num_opponents > 0:
                return PlayCardAction(card=attack[0])
            if skip:
                return PlayCardAction(card=skip[0])
            if see_future:
                return PlayCardAction(card=see_future[0])
            if shuffle:
                self._peek_ok = False
                return PlayCardAction(card=shuffle[0])
            return DrawCardAction()
        
        # HOARDING: Don't play cards unless necessary
        # Only play combos if we can target vulnerable opponent
        if my_defuse == 1 and kitten_prob > 0.20:
            # Try 5-different combo (valuable, no target needed)
            five_combo = self._find_five_different_combo(hand)
            if five_combo:
                return PlayComboAction(cards=five_combo)
            
            # Try 3-of-a-kind targeting vulnerable opponent
            three_combo = self._find_three_of_kind_combo(hand)
            if three_combo and num_opponents > 0:
                target = self._choose_target(view)
                if target and opponent_defuses.get(target, 0) == 0:
                    return PlayComboAction(cards=three_combo, target_player_id=target)
            
            # Try 2-of-a-kind targeting vulnerable opponent
            combo = self._find_combo(hand, prefer_type="two")
            if combo and num_opponents > 0:
                target = self._choose_target(view)
                if target and opponent_defuses.get(target, 0) == 0:
                    return PlayComboAction(cards=combo, target_player_id=target)
        
        # Default: DRAW (hoarding strategy - keep cards!)
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Track all events for perfect card counting."""
        t = event.event_type
        
        # Track peek results
        if t == EventType.CARDS_PEEKED and event.player_id == view.my_id:
            d: dict[str, Any] = event.data or {}
            types: Any = d.get("card_types", [])
            if isinstance(types, list):
                self._peek = [str(x) for x in types]  # type: ignore
                self._peek_ok = True
                self._draws = 0
                # Record cards seen
                for card_type in types:
                    self._card_counter.record_card_seen(str(card_type))
        
        if t == EventType.DECK_SHUFFLED:
            self._peek_ok = False
            self._peek = []
            self._draws = 0
        
        if t == EventType.CARD_DRAWN and self._peek_ok:
            self._draws += 1
        
        # Card counting: track all card plays
        if event.player_id and event.player_id != view.my_id:
            if t == EventType.CARD_PLAYED:
                card_type = (event.data or {}).get("card_type", "")
                if card_type:
                    self._card_counter.record_card_played(event.player_id, card_type)
            
            elif t == EventType.COMBO_PLAYED:
                # Track combo cards
                card_types = (event.data or {}).get("card_types", [])
                for ct in card_types:
                    self._card_counter.record_card_played(event.player_id, str(ct))
            
            elif t == EventType.EXPLODING_KITTEN_DEFUSED:
                self._card_counter.record_card_played(event.player_id, "DefuseCard")
            
            elif t == EventType.CARD_STOLEN:
                # We know exactly what opponent has
                target = (event.data or {}).get("target_player_id")
                card_type = (event.data or {}).get("card_type", "")
                if target == view.my_id:
                    # They stole from us
                    self._card_counter.record_card_stolen_from_us(event.player_id, card_type)
                elif target:
                    # They stole from someone else
                    self._card_counter.record_card_stolen_from_us(event.player_id, card_type)
            
            elif t == EventType.CARD_GIVEN:
                target = (event.data or {}).get("target_player_id")
                card_type = (event.data or {}).get("card_type", "")
                if target == view.my_id:
                    # We gave to them
                    self._card_counter.record_card_given_to_opponent(event.player_id, card_type)
            
            elif t == EventType.PLAYER_ELIMINATED:
                # They exploded - no defuse
                self._card_counter.record_no_defuse_on_explosion(event.player_id)
            
            elif t == EventType.REACTION_SKIPPED:
                # They could have Noped but didn't
                if event.player_id in view.other_players:
                    self._card_counter.record_no_nope(event.player_id, 0.3)
        
        # Initialize on game start
        if t == EventType.GAME_START:
            self._initial_deck_size = view.draw_pile_count
            # Initialize with deck config if available
            initial_counts = {
                "DefuseCard": 6,
                "NopeCard": 5,
                "AttackCard": 4,
                "SkipCard": 4,
                "FavorCard": 4,
                "ShuffleCard": 4,
                "SeeTheFutureCard": 5,
                "TacoCatCard": 4,
                "HairyPotatoCatCard": 4,
                "BeardCatCard": 4,
                "RainbowRalphingCatCard": 4,
                "CattermelonCard": 4,
            }
            self._card_counter.initialize(view.draw_pile_count, initial_counts)
    
    def react(self, view: BotView, event: GameEvent) -> Action | None:
        """Perfect information reaction."""
        nope = self._get_cards(view.my_hand, "NopeCard")
        if not nope:
            return None
        
        d = event.data or {}
        t = event.event_type
        
        # Always Nope combos targeting us
        if t == EventType.COMBO_PLAYED and d.get("target_player_id") == view.my_id:
            return PlayCardAction(card=nope[0])
        
        # Always Nope favors targeting us
        if t == EventType.FAVOR_REQUESTED and d.get("target_player_id") == view.my_id:
            return PlayCardAction(card=nope[0])
        
        # Nope attacks if we have no defuse or attacker is vulnerable
        if d.get("card_type") == "AttackCard":
            attacker_id = event.player_id
            if attacker_id:
                # Check if attacker has defuse (using card counter)
                hand_size = view.other_player_card_counts.get(attacker_id, 0)
                attacker_defuse, _ = self._card_counter.get_opponent_defuse_count(attacker_id, hand_size)
                
                # Nope if: we have no defuse OR attacker has no defuse (they'll explode)
                if self._defuse_count(view.my_hand) == 0 or attacker_defuse == 0:
                    return PlayCardAction(card=nope[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, size: int) -> int:
        """Perfect defuse positioning using card counting."""
        num_opponents = len(view.other_players)
        
        # Find most vulnerable opponent (no defuse)
        vulnerable_target: str | None = None
        for pid in view.other_players:
            hand_size = view.other_player_card_counts.get(pid, 0)
            defuse_count, confidence = self._card_counter.get_opponent_defuse_count(pid, hand_size)
            if defuse_count == 0 and confidence > 0.7:
                vulnerable_target = pid
                break
        
        if num_opponents == 1:
            return 0  # Endgame: top
        elif num_opponents == 2:
            if vulnerable_target:
                return min(1, size)  # Target vulnerable
            return min(2, size)
        else:
            if vulnerable_target:
                return min(1, size)  # Target vulnerable
            return min(2, size)
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """Give worst card (perfect information)."""
        hand = list(view.my_hand)
        
        # Sort by value (give worst first)
        return sorted(hand, key=lambda c: (
            1000 if c.card_type == "DefuseCard" else
            100 if c.card_type == "NopeCard" else
            50 if c.card_type == "AttackCard" else
            45 if c.card_type == "SkipCard" else
            40 if c.card_type == "FavorCard" else
            30 if c.card_type == "ShuffleCard" else
            20 if c.card_type == "SeeTheFutureCard" else
            1 if "Cat" in c.card_type else 10
        ))[0]
    
    def on_explode(self, view: BotView) -> None:
        """Last words."""
        view.say("Perfect information... insufficient.")
