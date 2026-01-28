"""
Mossad (Defuser) - rule-abiding, anti-explosion specialist.

Goal:
- Survive long matches by minimizing Exploding Kitten draws.
- Actively acquire/retain Defuse cards (Favor, combos).
- Use information (See the Future) to time draws and evasion.

This bot uses ONLY BotView-visible information and standard Actions.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

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


class MossadBot(Bot):
    """
    A defensive bot that prioritizes Defuse acquisition and safe draws.

    Key ideas:
    - Always maintain Defuse count when possible (never give away if avoidable).
    - Prefer SeeTheFuture before drawing when information is stale.
    - If top is risky (or we suspect it), use Skip/Attack/Shuffle to avoid drawing.
    - Use combos (2/3 of a kind, 5 different) primarily to acquire Defuse or deny
      vulnerable opponents.
    """

    def __init__(self) -> None:
        # Last peeked card types (from CARDS_PEEKED event)
        self._peek: list[str] = []
        self._peek_valid: bool = False
        self._draws_since_peek: int = 0

        # Track which opponents have used Defuse (public via events)
        self._defuse_used: dict[str, int] = defaultdict(int)

        # Track whether opponents often "Nope" (roughly)
        self._nope_seen: dict[str, int] = defaultdict(int)

    @property
    def name(self) -> str:
        # User requested: bot name must be "Mossad"
        return "Mossad"

    def _count(self, hand: tuple[Card, ...], card_type: str) -> int:
        return sum(1 for c in hand if c.card_type == card_type)

    def _cards(self, hand: tuple[Card, ...], card_type: str) -> list[Card]:
        return [c for c in hand if c.card_type == card_type]

    def _defuse_count(self, hand: tuple[Card, ...]) -> int:
        return self._count(hand, "DefuseCard")

    def _peek_top_type(self) -> str | None:
        if not self._peek_valid:
            return None
        if self._draws_since_peek >= len(self._peek):
            return None
        return self._peek[self._draws_since_peek]

    def _top_is_kitten(self) -> bool:
        top = self._peek_top_type()
        return top == "ExplodingKittenCard"

    def _top_is_safe(self) -> bool:
        top = self._peek_top_type()
        return top is not None and top != "ExplodingKittenCard"

    def _estimated_kitten_risk(self, view: BotView) -> float:
        # Conservative: kittens ~= number of opponents (engine uses players-1)
        opp = max(1, len(view.other_players))
        deck = max(1, view.draw_pile_count)
        return opp / deck

    def _target_most_vulnerable(self, view: BotView) -> str | None:
        """
        Prefer targeting an opponent who likely has 0 Defuse (used one already),
        otherwise target largest hand (best steal value).
        """
        if not view.other_players:
            return None

        # Heuristic: if opponent has already defused once, they may be out of Defuse.
        # (In this engine each player starts with 1 Defuse; extras exist but are rare.)
        vulnerable = [pid for pid in view.other_players if self._defuse_used.get(pid, 0) >= 1]
        if vulnerable:
            # choose among vulnerable by largest hand
            return max(vulnerable, key=lambda p: view.other_player_card_counts.get(p, 0))

        return max(view.other_players, key=lambda p: view.other_player_card_counts.get(p, 0))

    def _find_combo(
        self, hand: tuple[Card, ...]
    ) -> tuple[str, tuple[Card, ...]] | None:
        """
        Returns (combo_kind, cards):
        - "five_different"
        - "three_of_a_kind"
        - "two_of_a_kind"
        """
        combo_cards = [c for c in hand if c.can_combo()]
        if len(combo_cards) < 2:
            return None

        by_type: dict[str, list[Card]] = {}
        for c in combo_cards:
            by_type.setdefault(c.card_type, []).append(c)

        # 5 different types
        if len(by_type) >= 5:
            chosen: list[Card] = []
            for t in list(by_type.keys())[:5]:
                chosen.append(by_type[t][0])
            return ("five_different", tuple(chosen))

        # 3-of-a-kind preferred
        for cards in by_type.values():
            if len(cards) >= 3:
                return ("three_of_a_kind", tuple(cards[:3]))

        for cards in by_type.values():
            if len(cards) >= 2:
                return ("two_of_a_kind", tuple(cards[:2]))

        return None

    def take_turn(self, view: BotView) -> Action:
        hand = view.my_hand
        df = self._defuse_count(hand)
        risk = self._estimated_kitten_risk(view)

        skip = self._cards(hand, "SkipCard")
        attack = self._cards(hand, "AttackCard")
        shuffle = self._cards(hand, "ShuffleCard")
        see_future = self._cards(hand, "SeeTheFutureCard")
        favor = self._cards(hand, "FavorCard")

        # 1) If we know a kitten is on top, avoid drawing at almost any cost.
        if self._top_is_kitten():
            if shuffle:
                self._peek_valid = False
                return PlayCardAction(card=shuffle[0])
            if skip:
                return PlayCardAction(card=skip[0])
            if attack and view.other_players:
                return PlayCardAction(card=attack[0])
            if see_future:
                return PlayCardAction(card=see_future[0])
            # If we have Defuse, we can survive; otherwise, we risk elimination.
            return DrawCardAction()

        # 2) If peek is stale and we have info card, refresh before drawing.
        if see_future and not self._peek_valid:
            return PlayCardAction(card=see_future[0])

        # 3) If we know the top is safe, draw (fast progress, less random).
        if self._top_is_safe():
            self._draws_since_peek += 1
            return DrawCardAction()

        # 4) If we're low/no Defuse, aggressively seek Defuse via Favor/combos.
        #    (We can't ask for a named card in 3-of-kind in this engine; still good.)
        if df == 0:
            combo = self._find_combo(hand)
            if combo:
                kind, cards = combo
                if kind == "five_different":
                    return PlayComboAction(cards=cards)
                target = self._target_most_vulnerable(view)
                if target:
                    return PlayComboAction(cards=cards, target_player_id=target)

            if favor and view.other_players:
                target = self._target_most_vulnerable(view)
                if target:
                    return PlayCardAction(card=favor[0], target_player_id=target)

            # Avoid drawing if the deck is dangerous
            if risk >= 0.20:
                if skip:
                    return PlayCardAction(card=skip[0])
                if attack and view.other_players:
                    return PlayCardAction(card=attack[0])
                if shuffle:
                    self._peek_valid = False
                    return PlayCardAction(card=shuffle[0])

            return DrawCardAction()

        # 5) With Defuse in hand: be conservative (hoard power cards) unless risk is high.
        if risk >= 0.30:
            if skip:
                return PlayCardAction(card=skip[0])
            if attack and view.other_players:
                return PlayCardAction(card=attack[0])
            if shuffle:
                self._peek_valid = False
                return PlayCardAction(card=shuffle[0])

        # Opportunistic: if we have a clean 5-different combo, take discard value.
        combo = self._find_combo(hand)
        if combo and combo[0] == "five_different":
            return PlayComboAction(cards=combo[1])

        # Default: draw
        return DrawCardAction()

    def on_event(self, event: GameEvent, view: BotView) -> None:
        # Keep internal state synced with public events.
        if event.event_type == EventType.CARDS_PEEKED and event.player_id == view.my_id:
            data: dict[str, Any] = event.data or {}
            types_any: Any = data.get("card_types", [])
            if isinstance(types_any, list):
                self._peek = [str(x) for x in types_any]
                self._peek_valid = True
                self._draws_since_peek = 0

        if event.event_type == EventType.DECK_SHUFFLED:
            self._peek_valid = False
            self._peek = []
            self._draws_since_peek = 0

        if event.event_type == EventType.CARD_DRAWN and self._peek_valid:
            # Someone drew; our peek position likely advanced.
            self._draws_since_peek += 1

        if event.event_type == EventType.EXPLODING_KITTEN_DEFUSED:
            if event.player_id and event.player_id != view.my_id:
                self._defuse_used[event.player_id] += 1

        if event.event_type == EventType.CARD_PLAYED:
            if event.player_id and event.data.get("card_type") == "NopeCard":
                self._nope_seen[event.player_id] += 1

    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        # Defensive Nope policy: only when it directly harms us.
        nope_cards = self._cards(view.my_hand, "NopeCard")
        if not nope_cards:
            return None

        data = triggering_event.data or {}

        # Nope: Favor targeting us
        if triggering_event.event_type == EventType.FAVOR_REQUESTED:
            if data.get("target_player_id") == view.my_id:
                return PlayCardAction(card=nope_cards[0])

        # Nope: combo targeting us
        if triggering_event.event_type == EventType.COMBO_PLAYED:
            if data.get("target_player_id") == view.my_id:
                return PlayCardAction(card=nope_cards[0])

        # Nope: Attack when we are low on Defuse
        if data.get("card_type") == "AttackCard" and self._defuse_count(view.my_hand) == 0:
            return PlayCardAction(card=nope_cards[0])

        return None

    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        If we can reasonably eliminate opponents, put kitten near top.
        Otherwise, keep it safer (near bottom).
        """
        if len(view.other_players) <= 1:
            return 0

        # If many opponents have likely used Defuse, be aggressive.
        aggressive_targets = sum(1 for pid in view.other_players if self._defuse_used.get(pid, 0) >= 1)
        if aggressive_targets >= 2:
            return min(1, draw_pile_size)

        # Default: safer
        return draw_pile_size

    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """
        Never give away Defuse if avoidable; otherwise prefer giving cat cards.
        """
        hand = list(view.my_hand)
        # Prefer giving away cat cards first
        cats = [c for c in hand if "Cat" in c.card_type]
        if cats:
            return cats[0]

        # Avoid giving away Defuse/Nope
        non_critical = [c for c in hand if c.card_type not in ("DefuseCard", "NopeCard")]
        if non_critical:
            return non_critical[0]

        return hand[0]

    def on_explode(self, view: BotView) -> None:
        view.say("…")

