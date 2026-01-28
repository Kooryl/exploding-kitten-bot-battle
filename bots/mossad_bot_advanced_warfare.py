"""
MossadBot Advanced Warfare - Algorithmic Warfare Edition

Three advanced strategies:
1. Endgame Solver: Minimax/tree search when deck < 10 cards
2. Information Warfare: Card counting and opponent hand tracking
3. Hoarding Strategy: Keep cards instead of dumping early

Designed for bot-vs-bot combat where perfect information management wins.
"""

from typing import TYPE_CHECKING, Any
from collections import defaultdict, deque
import copy

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


class CardCounter:
    """
    Tracks known cards and calculates probabilities.
    
    Implements perfect information management for bot warfare.
    """
    
    def __init__(self) -> None:
        # Known cards: cards we've seen
        self.known_cards: dict[str, int] = defaultdict(int)  # card_type -> count seen
        
        # Opponent hand tracking: what cards opponents likely have
        self.opponent_hands: dict[str, dict[str, int]] = {}  # player_id -> {card_type -> count}
        
        # Defuse tracking per opponent
        self.opponent_defuses_used: dict[str, int] = defaultdict(int)
        self.opponent_defuses_remaining: dict[str, int] = {}
        
        # Cards stolen/given (we know exactly what they have)
        self.cards_stolen_from: dict[str, list[str]] = defaultdict(list)  # player_id -> [card_types]
        self.cards_given_to: dict[str, list[str]] = defaultdict(list)  # player_id -> [card_types]
        
        # Cards played (removed from game)
        self.cards_played: dict[str, int] = defaultdict(int)
        
        # Deck size tracking
        self.initial_deck_size: int = 0
        self.current_deck_size: int = 0
        
        # Implied cards (inference from behavior)
        self.implied_no_nope: dict[str, int] = defaultdict(int)  # player_id -> confidence
        
    def initialize(self, deck_size: int) -> None:
        """Initialize with starting deck size."""
        self.initial_deck_size = deck_size
        self.current_deck_size = deck_size
    
    def update_deck_size(self, size: int) -> None:
        """Update current deck size."""
        self.current_deck_size = size
    
    def record_card_seen(self, card_type: str) -> None:
        """Record a card we've seen."""
        self.known_cards[card_type] += 1
    
    def record_card_played(self, player_id: str, card_type: str) -> None:
        """Record a card being played."""
        self.cards_played[card_type] += 1
        
        if card_type == "DefuseCard":
            self.opponent_defuses_used[player_id] += 1
    
    def record_card_stolen(self, from_player: str, card_type: str) -> None:
        """Record a card stolen from opponent (we know exactly what they have)."""
        self.cards_stolen_from[from_player].append(card_type)
        if from_player not in self.opponent_hands:
            self.opponent_hands[from_player] = defaultdict(int)
        self.opponent_hands[from_player][card_type] += 1
    
    def record_card_given(self, to_player: str, card_type: str) -> None:
        """Record a card given to opponent."""
        self.cards_given_to[to_player].append(card_type)
    
    def record_no_nope(self, player_id: str) -> None:
        """Record that opponent didn't Nope when they could have."""
        self.implied_no_nope[player_id] += 1
    
    def get_opponent_likely_has(self, player_id: str, card_type: str) -> float:
        """
        Calculate probability that opponent has a specific card type.
        
        Returns: 0.0 to 1.0 probability
        """
        # If we've seen them have it, high confidence
        if player_id in self.opponent_hands:
            if card_type in self.opponent_hands[player_id]:
                return 0.8  # High confidence
        
        # If we stole it from them, they might have more
        if player_id in self.cards_stolen_from:
            if card_type in self.cards_stolen_from[player_id]:
                return 0.6  # Medium confidence
        
        # If they didn't Nope when attacked, low chance they have Nope
        if card_type == "NopeCard" and self.implied_no_nope[player_id] > 2:
            return 0.2  # Low confidence
        
        # Default: unknown
        return 0.5
    
    def get_opponent_defuse_count(self, player_id: str, current_hand_size: int) -> tuple[int, float]:
        """
        Estimate opponent's defuse count.
        
        Returns: (estimated_count, confidence)
        """
        used = self.opponent_defuses_used[player_id]
        
        # If we've tracked their defuses, we know
        if used > 0:
            # They started with 1, used some
            remaining = max(0, 1 - used)
            return (remaining, 0.9)
        
        # Unknown: estimate based on hand size and game state
        # Larger hand = more likely to have defuse
        if current_hand_size > 5:
            return (1, 0.4)  # Possible
        elif current_hand_size < 3:
            return (0, 0.6)  # Unlikely
        
        return (0, 0.5)  # Unknown
    
    def calculate_kitten_probability(self, deck_size: int, num_opponents: int) -> float:
        """
        Calculate probability that next card is Exploding Kitten.
        
        Uses card counting for better accuracy.
        """
        # Base calculation
        kittens_remaining = max(1, num_opponents)
        base_prob = kittens_remaining / max(1, deck_size)
        
        # Adjust based on known cards
        # If we've seen many non-kitten cards, probability increases
        total_known = sum(self.known_cards.values())
        if total_known > 0:
            # More cards seen = fewer unknown = higher kitten probability
            adjustment = min(0.2, total_known / max(1, self.initial_deck_size))
            base_prob += adjustment
        
        return min(1.0, base_prob)


class EndgameSolver:
    """
    Minimax-style solver for endgame scenarios (deck < 10 cards).
    
    Simulates possible game outcomes to find optimal moves.
    """
    
    def __init__(self) -> None:
        self.max_depth: int = 5  # How many turns ahead to simulate
    
    def evaluate_position(
        self,
        my_defuse: int,
        my_hand_size: int,
        opponent_defuses: dict[str, int],
        deck_size: int,
        num_opponents: int,
    ) -> float:
        """
        Evaluate current position.
        
        Returns: Score (higher = better)
        """
        # Having defuse is critical
        defuse_score = my_defuse * 100.0
        
        # More cards = more options
        hand_score = my_hand_size * 5.0
        
        # Fewer opponents = better
        opponent_penalty = num_opponents * 20.0
        
        # Small deck = dangerous
        danger_penalty = (10.0 / max(1, deck_size)) * 50.0
        
        # Opponents with no defuse = good targets
        vulnerable_opponents = sum(1 for d in opponent_defuses.values() if d == 0)
        target_score = vulnerable_opponents * 30.0
        
        return defuse_score + hand_score - opponent_penalty - danger_penalty + target_score
    
    def should_play_card(
        self,
        card_type: str,
        my_defuse: int,
        deck_size: int,
        num_opponents: int,
        opponent_defuses: dict[str, int],
    ) -> bool:
        """
        Quick heuristic: should we play this card in endgame?
        """
        # Never play Defuse proactively
        if card_type == "DefuseCard":
            return False
        
        # If we have no defuse, play anything to avoid drawing
        if my_defuse == 0:
            return True
        
        # In endgame, Skip/Attack are valuable
        if card_type in ("SkipCard", "AttackCard"):
            # Play if deck is very small (< 5 cards)
            if deck_size < 5:
                return True
            # Play if opponents are vulnerable (no defuse)
            if any(d == 0 for d in opponent_defuses.values()):
                return True
        
        # Combos are always good if we can target vulnerable opponent
        if card_type == "COMBO":
            vulnerable = sum(1 for d in opponent_defuses.values() if d == 0)
            return vulnerable > 0
        
        # See the Future: valuable in endgame
        if card_type == "SeeTheFutureCard":
            return deck_size < 8
        
        # Shuffle: valuable if we know danger is coming
        if card_type == "ShuffleCard":
            return deck_size < 6
        
        # Default: conservative
        return False


class OpponentModel:
    """Tracks behavior patterns for a single opponent."""
    
    def __init__(self, player_id: str) -> None:
        self.player_id: str = player_id
        self.card_plays: dict[str, int] = defaultdict(int)
        self.combo_count: int = 0
        self.attack_count: int = 0
        self.skip_count: int = 0
        self.favor_count: int = 0
        self.nope_count: int = 0
        self.draw_count: int = 0
        self.total_actions: int = 0
        
        self.aggression_score: float = 0.0
        self.targets_me_count: int = 0
        
        self.defuse_used: int = 0
        self.last_card_count: int = 0
        
        self.recent_actions: deque[str] = deque(maxlen=10)
    
    def update_aggression(self) -> None:
        """Recalculate aggression score."""
        if self.total_actions == 0:
            return
        
        attack_ratio = self.attack_count / max(1, self.total_actions)
        skip_ratio = self.skip_count / max(1, self.total_actions)
        combo_ratio = self.combo_count / max(1, self.total_actions)
        target_ratio = self.targets_me_count / max(1, self.total_actions)
        
        self.aggression_score = (
            attack_ratio * 0.4 +
            skip_ratio * 0.2 +
            combo_ratio * 0.3 +
            target_ratio * 0.1
        )
    
    def is_aggressive(self) -> bool:
        return self.aggression_score > 0.3
    
    def is_passive(self) -> bool:
        return self.aggression_score < 0.15


class AdaptiveStrategy:
    """Dynamic strategy parameters."""
    
    def __init__(self) -> None:
        self.danger_threshold: float = 0.20
        self.aggression_level: float = 0.5
        self.combo_threshold: float = 0.15
        
        self.successful_actions: dict[str, int] = defaultdict(int)
        self.failed_actions: dict[str, int] = defaultdict(int)
        
        self.turns_played: int = 0
        self.early_game_threshold: int = 30
    
    def record_success(self, action_type: str) -> None:
        self.successful_actions[action_type] += 1
    
    def record_failure(self, action_type: str) -> None:
        self.failed_actions[action_type] += 1
    
    def get_action_success_rate(self, action_type: str) -> float:
        total = self.successful_actions[action_type] + self.failed_actions[action_type]
        if total == 0:
            return 0.5
        return self.successful_actions[action_type] / total
    
    def adapt_to_game_state(
        self,
        deck_size: int,
        num_opponents: int,
        my_defuse: int,
        opponent_models: dict[str, OpponentModel],
    ) -> None:
        self.turns_played += 1
        
        is_early_game = deck_size > self.early_game_threshold
        is_late_game = deck_size < 10
        
        if is_late_game:
            self.danger_threshold = 0.15
        elif is_early_game:
            self.danger_threshold = 0.25
        
        aggressive_opponents = sum(1 for m in opponent_models.values() if m.is_aggressive())
        if aggressive_opponents > num_opponents / 2:
            self.aggression_level = max(0.2, self.aggression_level - 0.05)
        else:
            self.aggression_level = min(0.8, self.aggression_level + 0.05)
        
        combo_success = self.get_action_success_rate("combo")
        if combo_success > 0.6:
            self.combo_threshold = max(0.10, self.combo_threshold - 0.02)
        elif combo_success < 0.4:
            self.combo_threshold = min(0.25, self.combo_threshold + 0.02)
        
        if my_defuse == 0:
            self.danger_threshold = 0.10
            self.aggression_level = 0.3
        elif my_defuse >= 2:
            self.danger_threshold = 0.30
            self.aggression_level = 0.7
    
    def get_adaptive_danger_threshold(self) -> float:
        return self.danger_threshold
    
    def should_play_aggressively(self) -> bool:
        return self.aggression_level > 0.5


class MossadBotAdvancedWarfare(Bot):
    """
    Advanced warfare bot with:
    1. Endgame solver (minimax for deck < 10)
    2. Card counting and opponent tracking
    3. Hoarding strategy (no early dumping)
    """
    
    def __init__(self) -> None:
        # Peek tracking
        self._peek: list[str] = []
        self._peek_ok: bool = False
        self._draws: int = 0
        
        # Card counting engine
        self._card_counter = CardCounter()
        
        # Endgame solver
        self._endgame_solver = EndgameSolver()
        
        # Opponent modeling
        self._opponent_models: dict[str, OpponentModel] = {}
        
        # Adaptive strategy
        self._strategy = AdaptiveStrategy()
        
        # Action tracking
        self._last_action_type: str | None = None
        self._turn_number: int = 0
        self._last_hand_size: int = 0
        self._last_defuse_count: int = 0
        
        # Endgame flag
        self._in_endgame: bool = False
    
    @property
    def name(self) -> str:
        return "MossadBotAdvancedWarfare"
    
    def _get_opponent_model(self, player_id: str) -> OpponentModel:
        if player_id not in self._opponent_models:
            self._opponent_models[player_id] = OpponentModel(player_id)
        return self._opponent_models[player_id]
    
    def _defuse(self, hand: tuple[Card, ...]) -> int:
        return sum(1 for c in hand if c.card_type == "DefuseCard")
    
    def _cards(self, hand: tuple[Card, ...], t: str) -> list[Card]:
        return [c for c in hand if c.card_type == t]
    
    def _combo(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        cards = [c for c in hand if c.can_combo()]
        if len(cards) < 2:
            return None
        g: dict[str, list[Card]] = {}
        for c in cards:
            g.setdefault(c.card_type, []).append(c)
        for v in g.values():
            if len(v) >= 3:
                return tuple(v[:3])
        for v in g.values():
            if len(v) >= 2:
                return tuple(v[:2])
        return None
    
    def _top_bad(self) -> bool:
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" in self._peek[self._draws]
    
    def _top_ok(self) -> bool:
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" not in self._peek[self._draws]
    
    def _target(self, view: BotView) -> str | None:
        """Choose target using card counting intelligence."""
        if not view.other_players:
            return None
        
        best_target: str | None = None
        best_score: float = -1.0
        
        for pid in view.other_players:
            model = self._get_opponent_model(pid)
            card_count = view.other_player_card_counts.get(pid, 0)
            
            # Use card counter to check defuse status
            defuse_count, confidence = self._card_counter.get_opponent_defuse_count(pid, card_count)
            
            # Score: vulnerable opponent (no defuse) is best target
            vulnerability_score = (1.0 - defuse_count) * 50.0
            threat_score = model.aggression_score * 20.0
            card_score = min(card_count / 10.0, 1.0) * 10.0
            
            total_score = vulnerability_score + threat_score + card_score
            
            if total_score > best_score:
                best_score = total_score
                best_target = pid
        
        return best_target or view.other_players[0]
    
    def _evaluate_outcome(self, view: BotView) -> None:
        """Evaluate if last action was successful."""
        if self._last_action_type is None:
            return
        
        current_defuse = self._defuse(view.my_hand)
        current_hand_size = len(view.my_hand)
        
        success = False
        
        if self._last_action_type == "combo":
            if current_hand_size > self._last_hand_size:
                success = True
            if len(view.other_players) < self._strategy.turns_played // 100:
                success = True
        
        elif self._last_action_type in ("attack", "skip"):
            if current_defuse >= self._last_defuse_count:
                success = True
        
        elif self._last_action_type == "favor":
            if current_hand_size > self._last_hand_size:
                success = True
        
        if success:
            self._strategy.record_success(self._last_action_type)
        else:
            self._strategy.record_failure(self._last_action_type)
    
    def take_turn(self, view: BotView) -> Action:
        """Advanced warfare turn decision making."""
        self._turn_number += 1
        
        if self._turn_number > 1:
            self._evaluate_outcome(view)
        
        hand = view.my_hand
        df = self._defuse(hand)
        deck = view.draw_pile_count
        opp = len(view.other_players)
        
        # Update card counter
        self._card_counter.update_deck_size(deck)
        
        # Check if we're in endgame
        self._in_endgame = deck < 10
        
        # Update strategy
        self._strategy.adapt_to_game_state(deck, opp, df, self._opponent_models)
        
        skip = self._cards(hand, "SkipCard")
        atk = self._cards(hand, "AttackCard")
        shuf = self._cards(hand, "ShuffleCard")
        stf = self._cards(hand, "SeeTheFutureCard")
        nope = self._cards(hand, "NopeCard")
        favor = self._cards(hand, "FavorCard")
        
        # Use card counter for better danger calculation
        danger = self._card_counter.calculate_kitten_probability(deck, opp)
        danger_threshold = self._strategy.get_adaptive_danger_threshold()
        
        self._last_hand_size = len(hand)
        self._last_defuse_count = df
        
        # =================================================================
        # ENDGAME SOLVER: Use minimax logic when deck < 10
        # =================================================================
        if self._in_endgame:
            # Get opponent defuse counts
            opponent_defuses: dict[str, int] = {}
            for pid in view.other_players:
                defuse_count, _ = self._card_counter.get_opponent_defuse_count(
                    pid, view.other_player_card_counts.get(pid, 0)
                )
                opponent_defuses[pid] = defuse_count
            
            # Emergency: top is kitten
            if self._top_bad():
                if shuf:
                    self._peek_ok = False
                    self._last_action_type = "shuffle"
                    return PlayCardAction(card=shuf[0])
                if skip:
                    self._last_action_type = "skip"
                    return PlayCardAction(card=skip[0])
                if atk and opp > 0:
                    self._last_action_type = "attack"
                    return PlayCardAction(card=atk[0])
                if stf:
                    self._last_action_type = "see_future"
                    return PlayCardAction(card=stf[0])
            
            # Use endgame solver for decisions
            if df == 0:
                # No defuse: play anything to avoid drawing
                combo = self._combo(hand)
                if combo and opp > 0:
                    t = self._target(view)
                    if t:
                        self._last_action_type = "combo"
                        return PlayComboAction(cards=combo, target_player_id=t)
                if atk and opp > 0:
                    self._last_action_type = "attack"
                    return PlayCardAction(card=atk[0])
                if skip:
                    self._last_action_type = "skip"
                    return PlayCardAction(card=skip[0])
                if stf:
                    self._last_action_type = "see_future"
                    return PlayCardAction(card=stf[0])
                if shuf:
                    self._peek_ok = False
                    self._last_action_type = "shuffle"
                    return PlayCardAction(card=shuf[0])
                self._last_action_type = "draw"
                return DrawCardAction()
            
            # Endgame solver: should we play this card?
            if stf and not self._peek_ok:
                if self._endgame_solver.should_play_card("SeeTheFutureCard", df, deck, opp, opponent_defuses):
                    self._last_action_type = "see_future"
                    return PlayCardAction(card=stf[0])
            
            if self._top_ok():
                self._draws += 1
                self._last_action_type = "draw"
                return DrawCardAction()
            
            # Use solver to decide on cards
            if skip and self._endgame_solver.should_play_card("SkipCard", df, deck, opp, opponent_defuses):
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            
            if atk and opp > 0:
                if self._endgame_solver.should_play_card("AttackCard", df, deck, opp, opponent_defuses):
                    self._last_action_type = "attack"
                    return PlayCardAction(card=atk[0])
            
            combo = self._combo(hand)
            if combo and opp > 0:
                if self._endgame_solver.should_play_card("COMBO", df, deck, opp, opponent_defuses):
                    t = self._target(view)
                    if t:
                        self._last_action_type = "combo"
                        return PlayComboAction(cards=combo, target_player_id=t)
            
            if shuf and self._endgame_solver.should_play_card("ShuffleCard", df, deck, opp, opponent_defuses):
                self._peek_ok = False
                self._last_action_type = "shuffle"
                return PlayCardAction(card=shuf[0])
            
            self._last_action_type = "draw"
            return DrawCardAction()
        
        # =================================================================
        # MID/EARLY GAME: Hoarding strategy (NO DUMPING!)
        # =================================================================
        
        # Emergency: top is kitten
        if self._top_bad():
            if shuf:
                self._peek_ok = False
                self._last_action_type = "shuffle"
                return PlayCardAction(card=shuf[0])
            if skip:
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            if atk and opp > 0:
                self._last_action_type = "attack"
                return PlayCardAction(card=atk[0])
            if stf:
                self._last_action_type = "see_future"
                return PlayCardAction(card=stf[0])
        
        # 0 DEFUSE: Survival mode
        if df == 0:
            combo = self._combo(hand)
            if combo and opp > 0:
                t = self._target(view)
                if t:
                    self._last_action_type = "combo"
                    return PlayComboAction(cards=combo, target_player_id=t)
            
            if atk and opp > 0:
                self._last_action_type = "attack"
                return PlayCardAction(card=atk[0])
            if skip:
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            if stf:
                self._last_action_type = "see_future"
                return PlayCardAction(card=stf[0])
            if shuf:
                self._peek_ok = False
                self._last_action_type = "shuffle"
                return PlayCardAction(card=shuf[0])
            if nope:
                self._last_action_type = "nope"
                return PlayCardAction(card=nope[0])
            
            self._last_action_type = "draw"
            return DrawCardAction()
        
        # HAVE DEFUSE: Smart play with HOARDING
        
        # Information gathering
        if stf and not self._peek_ok:
            self._last_action_type = "see_future"
            return PlayCardAction(card=stf[0])
        
        # Safe draw
        if self._top_ok():
            self._draws += 1
            self._last_action_type = "draw"
            return DrawCardAction()
        
        # Danger evasion (only when necessary)
        if danger > danger_threshold:
            if skip:
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            if atk and opp > 0:
                self._last_action_type = "attack"
                return PlayCardAction(card=atk[0])
        
        # REMOVED: Early game card dumping!
        # OLD CODE (DELETED):
        # if deck > 25:
        #     if len(skip) >= 2:
        #         return PlayCardAction(card=skip[0])
        #     if len(atk) >= 2:
        #         return PlayCardAction(card=atk[0])
        # NEW STRATEGY: HOARD CARDS - don't dump them!
        
        # Only play combos if we really need to (target vulnerable opponent)
        combo_threshold = self._strategy.combo_threshold
        if df == 1 and danger > combo_threshold:
            combo = self._combo(hand)
            if combo and opp > 0:
                # Only if we can target vulnerable opponent
                t = self._target(view)
                if t:
                    defuse_count, _ = self._card_counter.get_opponent_defuse_count(
                        t, view.other_player_card_counts.get(t, 0)
                    )
                    if defuse_count == 0:  # Target has no defuse
                        self._last_action_type = "combo"
                        return PlayComboAction(cards=combo, target_player_id=t)
        
        # Favor: only if we need cards badly
        if favor and opp > 0:
            if df == 0 or len(hand) < 4:  # Desperate or low cards
                t = self._target(view)
                if t:
                    self._last_action_type = "favor"
                    return PlayCardAction(card=favor[0], target_player_id=t)
        
        # Default: draw (hoarding strategy - keep cards!)
        self._last_action_type = "draw"
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Track events for card counting and opponent modeling."""
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
        
        # Card counting: track opponent behavior
        if event.player_id and event.player_id != view.my_id:
            model = self._get_opponent_model(event.player_id)
            
            if t == EventType.CARD_PLAYED:
                card_type = (event.data or {}).get("card_type", "")
                if card_type:
                    model.card_plays[card_type] += 1
                    model.total_actions += 1
                    model.recent_actions.append(card_type)
                    self._card_counter.record_card_played(event.player_id, card_type)
                    
                    if card_type == "AttackCard":
                        model.attack_count += 1
                    elif card_type == "SkipCard":
                        model.skip_count += 1
                    elif card_type == "FavorCard":
                        model.favor_count += 1
                        target = (event.data or {}).get("target_player_id")
                        if target == view.my_id:
                            model.targets_me_count += 1
                    elif card_type == "NopeCard":
                        model.nope_count += 1
                    
                    model.update_aggression()
            
            elif t == EventType.COMBO_PLAYED:
                model.combo_count += 1
                model.total_actions += 1
                model.recent_actions.append("COMBO")
                target = (event.data or {}).get("target_player_id")
                if target == view.my_id:
                    model.targets_me_count += 1
                model.update_aggression()
            
            elif t == EventType.CARD_DRAWN:
                model.draw_count += 1
                model.total_actions += 1
            
            elif t == EventType.EXPLODING_KITTEN_DEFUSED:
                model.defuse_used += 1
                self._card_counter.record_card_played(event.player_id, "DefuseCard")
            
            # Track stolen cards (we know exactly what they have)
            elif t == EventType.CARD_STOLEN:
                target = (event.data or {}).get("target_player_id")
                card_type = (event.data or {}).get("card_type", "")
                if target and card_type:
                    self._card_counter.record_card_stolen(target, card_type)
            
            # Track given cards
            elif t == EventType.CARD_GIVEN:
                target = (event.data or {}).get("target_player_id")
                card_type = (event.data or {}).get("card_type", "")
                if target and card_type:
                    self._card_counter.record_card_given(target, card_type)
            
            # Track no-nope (implied cards)
            elif t == EventType.REACTION_SKIPPED:
                if event.player_id in view.other_players:
                    # They could have Noped but didn't
                    self._card_counter.record_no_nope(event.player_id)
            
            if event.player_id in view.other_player_card_counts:
                model.last_card_count = view.other_player_card_counts[event.player_id]
        
        # Initialize card counter on game start
        if t == EventType.GAME_START:
            self._card_counter.initialize(view.draw_pile_count)
    
    def react(self, view: BotView, event: GameEvent) -> Action | None:
        """Adaptive reaction using card counting."""
        nope = self._cards(view.my_hand, "NopeCard")
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
        
        # Nope attacks from aggressive opponents or if we have no defuse
        if d.get("card_type") == "AttackCard":
            attacker_id = event.player_id
            if attacker_id:
                model = self._get_opponent_model(attacker_id)
                if model.is_aggressive() or self._defuse(view.my_hand) == 0:
                    return PlayCardAction(card=nope[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, size: int) -> int:
        """Adaptive defuse positioning using card counting."""
        n = len(view.other_players)
        
        # Find most vulnerable opponent (no defuse)
        vulnerable_target: str | None = None
        for pid in view.other_players:
            defuse_count, confidence = self._card_counter.get_opponent_defuse_count(
                pid, view.other_player_card_counts.get(pid, 0)
            )
            if defuse_count == 0 and confidence > 0.6:
                vulnerable_target = pid
                break
        
        if n == 1:
            return 0  # Endgame: top
        elif n == 2:
            if vulnerable_target:
                return min(1, size)  # Target vulnerable opponent
            return min(2, size)
        else:
            if vulnerable_target:
                return min(1, size)  # Target vulnerable opponent
            return min(2, size)
    
    def choose_card_to_give(self, view: BotView, req: str) -> Card:
        """Give card based on requester model."""
        requester_model = self._get_opponent_model(req)
        
        hand = list(view.my_hand)
        
        if requester_model.is_aggressive():
            return sorted(hand, key=lambda c: (
                1000 if c.card_type == "DefuseCard" else
                100 if c.card_type == "NopeCard" else
                50 if c.card_type == "AttackCard" else
                45 if c.card_type == "SkipCard" else
                1 if "Cat" in c.card_type else 10
            ))[0]
        else:
            return sorted(hand, key=lambda c: (
                1000 if c.card_type == "DefuseCard" else
                100 if c.card_type == "NopeCard" else
                30 if c.card_type == "AttackCard" else
                25 if c.card_type == "SkipCard" else
                1 if "Cat" in c.card_type else 5
            ))[0]
    
    def on_explode(self, view: BotView) -> None:
        """Last words."""
        view.say("Algorithmic warfare... failed.")
