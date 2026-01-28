"""
MossadBot Adaptive - In-Game Learning and Evolution

This bot evolves during the game by:
1. Tracking opponent behavior patterns
2. Adapting strategy parameters based on what works
3. Learning from successful/unsuccessful actions
4. Adjusting decision thresholds dynamically
5. Modeling opponent strategies

Designed for long games (1000+ rounds) against other coded bots.
"""

from typing import TYPE_CHECKING, Any
from collections import defaultdict, deque

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


class OpponentModel:
    """Tracks behavior patterns for a single opponent."""
    
    def __init__(self, player_id: str) -> None:
        self.player_id: str = player_id
        self.card_plays: dict[str, int] = defaultdict(int)  # card_type -> count
        self.combo_count: int = 0
        self.attack_count: int = 0
        self.skip_count: int = 0
        self.favor_count: int = 0
        self.nope_count: int = 0
        self.draw_count: int = 0
        self.total_actions: int = 0
        
        # Aggression metrics
        self.aggression_score: float = 0.0  # 0.0 = passive, 1.0 = very aggressive
        self.targets_me_count: int = 0  # How often they target us
        
        # Defuse tracking
        self.defuse_used: int = 0
        self.last_card_count: int = 0
        
        # Recent actions (for pattern detection)
        self.recent_actions: deque[str] = deque(maxlen=10)
    
    def update_aggression(self) -> None:
        """Recalculate aggression score based on behavior."""
        if self.total_actions == 0:
            return
        
        # Aggression indicators:
        # - High attack/skip usage
        # - Frequent combos
        # - Targeting us often
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
        """Check if opponent is aggressive."""
        return self.aggression_score > 0.3
    
    def is_passive(self) -> bool:
        """Check if opponent is passive."""
        return self.aggression_score < 0.15


class AdaptiveStrategy:
    """Dynamic strategy parameters that evolve during the game."""
    
    def __init__(self) -> None:
        # Base thresholds (will adapt)
        self.danger_threshold: float = 0.20  # When to use evasion
        self.aggression_level: float = 0.5  # How aggressive to be
        self.combo_threshold: float = 0.15  # When to play combos
        
        # Learning from outcomes
        self.successful_actions: dict[str, int] = defaultdict(int)
        self.failed_actions: dict[str, int] = defaultdict(int)
        
        # Adaptation history
        self.adaptation_history: list[tuple[int, dict[str, float]]] = []
        
        # Game phase tracking
        self.turns_played: int = 0
        self.early_game_threshold: int = 30  # Deck size for early game
        
        # Opponent threat levels
        self.opponent_threats: dict[str, float] = {}
    
    def record_success(self, action_type: str) -> None:
        """Record a successful action."""
        self.successful_actions[action_type] += 1
    
    def record_failure(self, action_type: str) -> None:
        """Record a failed action."""
        self.failed_actions[action_type] += 1
    
    def get_action_success_rate(self, action_type: str) -> float:
        """Get success rate for an action type."""
        total = self.successful_actions[action_type] + self.failed_actions[action_type]
        if total == 0:
            return 0.5  # Neutral if no data
        return self.successful_actions[action_type] / total
    
    def adapt_to_game_state(
        self,
        deck_size: int,
        num_opponents: int,
        my_defuse: int,
        opponent_models: dict[str, OpponentModel],
    ) -> None:
        """Adapt strategy based on current game state."""
        self.turns_played += 1
        
        # Phase detection
        is_early_game = deck_size > self.early_game_threshold
        is_late_game = deck_size < 10
        
        # Adapt danger threshold based on game phase
        if is_late_game:
            self.danger_threshold = 0.15  # More cautious late game
        elif is_early_game:
            self.danger_threshold = 0.25  # More risk-tolerant early
        
        # Adapt aggression based on opponent behavior
        aggressive_opponents = sum(1 for m in opponent_models.values() if m.is_aggressive())
        if aggressive_opponents > num_opponents / 2:
            # Most opponents are aggressive - be more defensive
            self.aggression_level = max(0.2, self.aggression_level - 0.05)
        else:
            # Opponents are passive - can be more aggressive
            self.aggression_level = min(0.8, self.aggression_level + 0.05)
        
        # Adapt combo threshold based on success rate
        combo_success = self.get_action_success_rate("combo")
        if combo_success > 0.6:
            self.combo_threshold = max(0.10, self.combo_threshold - 0.02)
        elif combo_success < 0.4:
            self.combo_threshold = min(0.25, self.combo_threshold + 0.02)
        
        # Adapt based on my defuse count
        if my_defuse == 0:
            self.danger_threshold = 0.10  # Very cautious with no defuse
            self.aggression_level = 0.3  # Less aggressive
        elif my_defuse >= 2:
            self.danger_threshold = 0.30  # Can take more risks
            self.aggression_level = 0.7  # More aggressive
    
    def get_adaptive_danger_threshold(self) -> float:
        """Get current danger threshold."""
        return self.danger_threshold
    
    def should_play_aggressively(self) -> bool:
        """Check if we should play aggressively."""
        return self.aggression_level > 0.5


class MossadBotAdaptive(Bot):
    """Adaptive bot that learns and evolves during the game."""
    
    def __init__(self) -> None:
        # Peek tracking
        self._peek: list[str] = []
        self._peek_ok: bool = False
        self._draws: int = 0
        
        # Opponent modeling
        self._opponent_models: dict[str, OpponentModel] = {}
        
        # Adaptive strategy
        self._strategy = AdaptiveStrategy()
        
        # Action tracking for learning
        self._last_action_type: str | None = None
        self._last_action_turn: int = 0
        
        # Outcome tracking
        self._turn_number: int = 0
        self._last_hand_size: int = 0
        self._last_defuse_count: int = 0
    
    @property
    def name(self) -> str:
        return "MossadBotAdaptive"
    
    def _get_opponent_model(self, player_id: str) -> OpponentModel:
        """Get or create opponent model."""
        if player_id not in self._opponent_models:
            self._opponent_models[player_id] = OpponentModel(player_id)
        return self._opponent_models[player_id]
    
    def _defuse(self, hand: tuple[Card, ...]) -> int:
        """Count Defuse cards."""
        return sum(1 for c in hand if c.card_type == "DefuseCard")
    
    def _cards(self, hand: tuple[Card, ...], t: str) -> list[Card]:
        """Filter cards by type."""
        return [c for c in hand if c.card_type == t]
    
    def _combo(self, hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
        """Find best combo."""
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
        """Check if next card is Exploding Kitten."""
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" in self._peek[self._draws]
    
    def _top_ok(self) -> bool:
        """Check if next card is safe."""
        if not self._peek_ok or not self._peek:
            return False
        if self._draws >= len(self._peek):
            return False
        return "ExplodingKittenCard" not in self._peek[self._draws]
    
    def _target(self, view: BotView) -> str | None:
        """Choose target based on opponent models."""
        if not view.other_players:
            return None
        
        # Prefer targeting aggressive opponents (they're threats)
        # Or opponents with many cards (good combo targets)
        best_target: str | None = None
        best_score: float = -1.0
        
        for pid in view.other_players:
            model = self._get_opponent_model(pid)
            card_count = view.other_player_card_counts.get(pid, 0)
            
            # Score: threat level + card count
            threat_score = model.aggression_score * 0.5
            card_score = min(card_count / 10.0, 1.0) * 0.5
            total_score = threat_score + card_score
            
            if total_score > best_score:
                best_score = total_score
                best_target = pid
        
        return best_target or view.other_players[0]
    
    def _evaluate_outcome(self, view: BotView) -> None:
        """Evaluate if last action was successful."""
        if self._last_action_type is None:
            return
        
        # Check if we're in a better state
        current_defuse = self._defuse(view.my_hand)
        current_hand_size = len(view.my_hand)
        
        # Success indicators:
        # - Gained a Defuse card
        # - Hand size increased (stole cards)
        # - Still alive (didn't explode)
        # - Opponents eliminated
        
        success = False
        
        if self._last_action_type == "combo":
            # Combo success: gained cards or opponent eliminated
            if current_hand_size > self._last_hand_size:
                success = True
            if len(view.other_players) < self._strategy.turns_played // 100:
                success = True
        
        elif self._last_action_type in ("attack", "skip"):
            # Evasion success: avoided drawing, still alive
            if current_defuse >= self._last_defuse_count:
                success = True
        
        elif self._last_action_type == "favor":
            # Favor success: got a useful card
            if current_hand_size > self._last_hand_size:
                success = True
        
        # Record outcome
        if success:
            self._strategy.record_success(self._last_action_type)
        else:
            self._strategy.record_failure(self._last_action_type)
    
    def take_turn(self, view: BotView) -> Action:
        """Adaptive turn decision making."""
        self._turn_number += 1
        
        # Evaluate previous action outcome
        if self._turn_number > 1:
            self._evaluate_outcome(view)
        
        hand = view.my_hand
        df = self._defuse(hand)
        deck = view.draw_pile_count
        opp = len(view.other_players)
        
        # Update strategy based on current state
        self._strategy.adapt_to_game_state(
            deck, opp, df, self._opponent_models
        )
        
        skip = self._cards(hand, "SkipCard")
        atk = self._cards(hand, "AttackCard")
        shuf = self._cards(hand, "ShuffleCard")
        stf = self._cards(hand, "SeeTheFutureCard")
        nope = self._cards(hand, "NopeCard")
        favor = self._cards(hand, "FavorCard")
        
        # Calculate adaptive danger
        kittens = max(1, opp)
        danger = kittens / max(1, deck)
        danger_threshold = self._strategy.get_adaptive_danger_threshold()
        
        # Store state for outcome evaluation
        self._last_hand_size = len(hand)
        self._last_defuse_count = df
        
        # =================================================================
        # TOP IS KITTEN - Emergency evasion
        # =================================================================
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
        
        # =================================================================
        # 0 DEFUSE - Survival mode
        # =================================================================
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
        
        # =================================================================
        # HAVE DEFUSE - Adaptive smart play
        # =================================================================
        
        # Information gathering
        if stf and not self._peek_ok:
            self._last_action_type = "see_future"
            return PlayCardAction(card=stf[0])
        
        # Safe draw
        if self._top_ok():
            self._draws += 1
            self._last_action_type = "draw"
            return DrawCardAction()
        
        # Adaptive danger evasion
        if danger > danger_threshold:
            if skip:
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            if atk and opp > 0:
                self._last_action_type = "attack"
                return PlayCardAction(card=atk[0])
        
        # Adaptive aggression based on strategy
        should_aggress = self._strategy.should_play_aggressively()
        
        if should_aggress and deck > 25:
            # Aggressive early game: dump cards
            if len(skip) >= 2:
                self._last_action_type = "skip"
                return PlayCardAction(card=skip[0])
            if len(atk) >= 2 and opp > 0:
                self._last_action_type = "attack"
                return PlayCardAction(card=atk[0])
        
        # Adaptive combo play
        combo_threshold = self._strategy.combo_threshold
        if df == 1 and danger > combo_threshold:
            combo = self._combo(hand)
            if combo and opp > 0:
                t = self._target(view)
                if t:
                    self._last_action_type = "combo"
                    return PlayComboAction(cards=combo, target_player_id=t)
        
        # Favor cards: use if aggressive or need cards
        if favor and opp > 0:
            if should_aggress or df == 0:
                t = self._target(view)
                if t:
                    self._last_action_type = "favor"
                    return PlayCardAction(card=favor[0], target_player_id=t)
        
        # Default: draw
        self._last_action_type = "draw"
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Track all events for opponent modeling and learning."""
        t = event.event_type
        
        # Track peek results
        if t == EventType.CARDS_PEEKED and event.player_id == view.my_id:
            d: dict[str, Any] = event.data or {}
            types: Any = d.get("card_types", [])
            if isinstance(types, list):
                self._peek = [str(x) for x in types]  # type: ignore
                self._peek_ok = True
                self._draws = 0
        
        if t == EventType.DECK_SHUFFLED:
            self._peek_ok = False
            self._peek = []
            self._draws = 0
        
        if t == EventType.CARD_DRAWN and self._peek_ok:
            self._draws += 1
        
        # Track opponent behavior
        if event.player_id and event.player_id != view.my_id:
            model = self._get_opponent_model(event.player_id)
            
            if t == EventType.CARD_PLAYED:
                card_type = (event.data or {}).get("card_type", "")
                if card_type:
                    model.card_plays[card_type] += 1
                    model.total_actions += 1
                    model.recent_actions.append(card_type)
                    
                    if card_type == "AttackCard":
                        model.attack_count += 1
                    elif card_type == "SkipCard":
                        model.skip_count += 1
                    elif card_type == "FavorCard":
                        model.favor_count += 1
                        # Check if targeting us
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
                # Check if targeting us
                target = (event.data or {}).get("target_player_id")
                if target == view.my_id:
                    model.targets_me_count += 1
                model.update_aggression()
            
            elif t == EventType.CARD_DRAWN:
                model.draw_count += 1
                model.total_actions += 1
            
            elif t == EventType.EXPLODING_KITTEN_DEFUSED:
                model.defuse_used += 1
            
            # Update card count tracking
            if event.player_id in view.other_player_card_counts:
                model.last_card_count = view.other_player_card_counts[event.player_id]
    
    def react(self, view: BotView, event: GameEvent) -> Action | None:
        """Adaptive reaction based on opponent models."""
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
                # Nope if: aggressive opponent OR we have no defuse
                if model.is_aggressive() or self._defuse(view.my_hand) == 0:
                    return PlayCardAction(card=nope[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, size: int) -> int:
        """Adaptive defuse positioning."""
        n = len(view.other_players)
        
        # Target aggressive opponents first
        aggressive_count = sum(1 for m in self._opponent_models.values() if m.is_aggressive())
        
        if n == 1:
            return 0  # Endgame: top
        elif n == 2:
            # If remaining opponent is aggressive, put it closer to top
            if aggressive_count > 0:
                return min(1, size)
            return min(2, size)
        else:
            # Early game: position based on threat
            if aggressive_count >= n / 2:
                return min(1, size)  # More aggressive = closer to top
            return min(2, size)
    
    def choose_card_to_give(self, view: BotView, req: str) -> Card:
        """Adaptive card giving based on requester model."""
        requester_model = self._get_opponent_model(req)
        
        # If requester is aggressive, give worse cards
        # If passive, can give slightly better cards
        hand = list(view.my_hand)
        
        if requester_model.is_aggressive():
            # Aggressive opponent: give worst cards
            return sorted(hand, key=lambda c: (
                1000 if c.card_type == "DefuseCard" else
                100 if c.card_type == "NopeCard" else
                50 if c.card_type == "AttackCard" else
                45 if c.card_type == "SkipCard" else
                1 if "Cat" in c.card_type else 10
            ))[0]
        else:
            # Passive opponent: can give slightly better (but still not best)
            return sorted(hand, key=lambda c: (
                1000 if c.card_type == "DefuseCard" else
                100 if c.card_type == "NopeCard" else
                30 if c.card_type == "AttackCard" else
                25 if c.card_type == "SkipCard" else
                1 if "Cat" in c.card_type else 5
            ))[0]
    
    def on_explode(self, view: BotView) -> None:
        """Last words."""
        view.say("Adaptation failed...")
