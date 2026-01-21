"""
MossadBot Advanced v6 - Aggressive Early Game

New strategy:
- Early game: Play cards aggressively to thin deck
- Late game: Conserve and survive
- Always use See the Future before drawing
- Attack/Skip liberally when have Defuse
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


class MossadBotAdvanced(Bot):
    """Aggressive early, conservative late."""
    
    def __init__(self) -> None:
        self._peek: list[str] = []
        self._peek_ok: bool = False
        self._draws: int = 0
    
    @property
    def name(self) -> str:
        return "MossadBotAdvanced"
    
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
        if not view.other_players:
            return None
        return max(view.other_players, key=lambda p: view.other_player_card_counts.get(p, 0))
    
    def take_turn(self, view: BotView) -> Action:
        hand = view.my_hand
        df = self._defuse(hand)
        deck = view.draw_pile_count
        opp = len(view.other_players)
        
        skip = self._cards(hand, "SkipCard")
        atk = self._cards(hand, "AttackCard")
        shuf = self._cards(hand, "ShuffleCard")
        stf = self._cards(hand, "SeeTheFutureCard")
        nope = self._cards(hand, "NopeCard")
        
        # Danger estimate: (kittens) / deck
        kittens = max(1, opp)  # approx number of kittens
        danger = kittens / max(1, deck)
        
        # =================================================================
        # TOP IS KITTEN - deal with it
        # =================================================================
        if self._top_bad():
            if shuf:
                self._peek_ok = False
                return PlayCardAction(card=shuf[0])
            if skip:
                return PlayCardAction(card=skip[0])
            if atk and opp > 0:
                return PlayCardAction(card=atk[0])
            if stf:
                return PlayCardAction(card=stf[0])
        
        # =================================================================
        # 0 DEFUSE - SURVIVAL MODE
        # =================================================================
        if df == 0:
            combo = self._combo(hand)
            if combo and opp > 0:
                t = self._target(view)
                if t:
                    return PlayComboAction(cards=combo, target_player_id=t)
            
            if atk and opp > 0:
                return PlayCardAction(card=atk[0])
            if skip:
                return PlayCardAction(card=skip[0])
            if stf:
                return PlayCardAction(card=stf[0])
            if shuf:
                self._peek_ok = False
                return PlayCardAction(card=shuf[0])
            if nope:
                return PlayCardAction(card=nope[0])
            
            return DrawCardAction()
        
        # =================================================================
        # HAVE DEFUSE - PLAY SMART
        # =================================================================
        
        # Always use See the Future before drawing if we don't have info
        if stf and not self._peek_ok:
            return PlayCardAction(card=stf[0])
        
        # If we know it's safe, draw
        if self._top_ok():
            self._draws += 1
            return DrawCardAction()
        
        # If deck is dangerous (>20% kitten chance), use evasion
        if danger > 0.20:
            if skip:
                return PlayCardAction(card=skip[0])
            if atk and opp > 0:
                return PlayCardAction(card=atk[0])
        
        # Early game (big deck): be more aggressive with cards
        if deck > 25:
            # Dump excess cards
            if len(skip) >= 2:
                return PlayCardAction(card=skip[0])
            if len(atk) >= 2 and opp > 0:
                return PlayCardAction(card=atk[0])
        
        # Mid game: use combos if we only have 1 defuse
        if df == 1 and danger > 0.15:
            combo = self._combo(hand)
            if combo and opp > 0:
                t = self._target(view)
                if t:
                    return PlayComboAction(cards=combo, target_player_id=t)
        
        # Default: draw
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        t = event.event_type
        
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
    
    def react(self, view: BotView, event: GameEvent) -> Action | None:
        nope = self._cards(view.my_hand, "NopeCard")
        if not nope:
            return None
        
        d = event.data or {}
        t = event.event_type
        
        if t == EventType.COMBO_PLAYED and d.get("target_player_id") == view.my_id:
            return PlayCardAction(card=nope[0])
        if t == EventType.FAVOR_REQUESTED and d.get("target_player_id") == view.my_id:
            return PlayCardAction(card=nope[0])
        if d.get("card_type") == "AttackCard" and self._defuse(view.my_hand) == 0:
            return PlayCardAction(card=nope[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, size: int) -> int:
        n = len(view.other_players)
        if n == 1:
            return 0
        if n == 2:
            return min(1, size)
        return min(2, size)
    
    def choose_card_to_give(self, view: BotView, req: str) -> Card:
        return sorted(view.my_hand, key=lambda c: (
            1000 if c.card_type == "DefuseCard" else
            100 if c.card_type == "NopeCard" else
            50 if c.card_type == "AttackCard" else
            45 if c.card_type == "SkipCard" else
            1 if "Cat" in c.card_type else 10
        ))[0]
    
    def on_explode(self, view: BotView) -> None:
        view.say("...")
