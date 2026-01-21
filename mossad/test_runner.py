"""
Test Runner - 5-Player Battle Royale (1 MossadBot vs 4 RandomBots)
"""

import time
from pathlib import Path
from typing import Any

from game.bots.loader import BotLoader
from game.engine import GameEngine
from game.history import EventType


class TestRunner:
    """Run 5-player games efficiently and collect detailed statistics."""
    
    def __init__(self, games_to_run: int = 100) -> None:
        """Initialize test runner."""
        self.games_to_run = games_to_run
        # Path relative to project root
        self.deck_config = Path(__file__).parent.parent / "configs" / "default_deck.json"
    
    def run_single_game(self, game_id: int) -> dict[str, Any]:
        """Run a single 5-player game: 1 MossadBot vs 4 RandomBots."""
        seed = (game_id * 1000) % (2**31)
        
        # Create engine in quiet mode
        engine = GameEngine(seed=seed, quiet_mode=True, chat_enabled=False, bot_timeout=None)
        
        # Load bots (force reload by clearing module cache)
        import sys
        # Clear any cached mossad_bot module to force reload
        module_keys = [k for k in sys.modules.keys() if 'mossad_bot' in k.lower()]
        for key in module_keys:
            del sys.modules[key]
        
        loader = BotLoader()
        # Paths relative to project root
        project_root = Path(__file__).parent.parent
        hero_bot = loader.load_from_file(project_root / "bots" / "mossad_bot.py")[0]
        random_bot_class = loader.load_from_file(project_root / "bots" / "random_bot.py")[0]
        
        hero_base_name = hero_bot.name
        
        # Add 1 hero + 4 random bots
        engine.add_bot(hero_bot)
        for i in range(4):
            engine.add_bot(type(random_bot_class)())
        
        # Get hero player ID
        hero_id = None
        for pid in engine._bots.keys():
            if pid.startswith(hero_base_name):
                hero_id = pid
                break
        
        # Load deck
        if self.deck_config.exists():
            deck = engine.registry.create_deck_from_file(self.deck_config)
            engine._state._draw_pile = deck
            engine._rng.shuffle(engine._state._draw_pile)
        
        # Run game
        winner = engine.run()
        
        # Extract elimination order from history
        elimination_order: list[str] = []
        for event in engine.history.get_events():
            if event.event_type == EventType.PLAYER_ELIMINATED:
                if event.player_id:
                    elimination_order.append(event.player_id)
        
        # Placement order: winner first (1st), then reverse elimination order
        # Last eliminated = 2nd place, first eliminated = 5th place
        placements: list[str] = [winner] + list(reversed(elimination_order)) if winner else []
        
        # Find hero's placement
        hero_placement = 5
        hero_won = False
        if hero_id:
            if winner == hero_id:
                hero_won = True
                hero_placement = 1
            elif hero_id in placements:
                hero_placement = placements.index(hero_id) + 1
        
        # Get final hand state
        hero_final_defuse_count = 0
        hero_final_hand_size = 0
        if hero_id and hero_id in engine._state.players:
            player_state = engine._state.players[hero_id]
            if player_state:
                hero_final_hand_size = len(player_state.hand)
                hero_final_defuse_count = sum(
                    1 for c in player_state.hand if c.card_type == "DefuseCard"
                )
        
        # Count total turns
        total_turns = sum(
            1 for event in engine.history.get_events()
            if event.event_type == EventType.TURN_START
        )
        
        return {
            "game_id": game_id,
            "seed": seed,
            "won": hero_won,
            "placement": hero_placement,
            "total_turns": total_turns,
            "final_hand_size": hero_final_hand_size,
            "final_defuse_count": hero_final_defuse_count,
            "elimination_order": elimination_order,
            "placements": placements,
        }
    
    def run_tests(self) -> dict[str, Any]:
        """Execute games and collect statistics."""
        print(f"Running {self.games_to_run} games (1v4 Battle Royale)...", end="", flush=True)
        results = []
        start_time = time.time()
        
        for i in range(self.games_to_run):
            try:
                stats = self.run_single_game(i)
                results.append(stats)
            except Exception as e:
                # Skip failed games
                continue
        
        duration = time.time() - start_time
        wins = sum(1 for r in results if r.get("won", False))
        win_rate = wins / len(results) if results else 0.0
        
        # Calculate average placement
        placements = [r.get("placement", 5) for r in results]
        avg_placement = sum(placements) / len(placements) if placements else 5.0
        
        # Calculate placement distribution
        placement_dist = {}
        for r in results:
            place = r.get("placement", 5)
            placement_dist[place] = placement_dist.get(place, 0) + 1
        
        print(f" Done ({duration:.2f}s). Win Rate: {win_rate:.1%} | Avg Place: {avg_placement:.1f}")
        
        return {
            "win_rate": win_rate,
            "avg_placement": avg_placement,
            "total_games": len(results),
            "wins": wins,
            "losses": len(results) - wins,
            "placement_distribution": placement_dist,
            "games": results,
        }
