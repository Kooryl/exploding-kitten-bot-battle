"""
Game Simulator - High-Performance Arena for Bot Testing

This module provides efficient parallel game simulation for testing
bot weights and configurations.
"""

import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


def _run_single_game(args: tuple[dict[str, float], int]) -> dict[str, Any]:
    """
    Run a single game with the given weights.
    
    This function is designed to run in a separate process.
    
    Args:
        args: Tuple of (hero_weights, seed)
    
    Returns:
        Dict with game results.
    """
    hero_weights, seed = args
    
    # Import inside function to avoid pickling issues
    from game.bots.loader import BotLoader
    from game.engine import GameEngine
    from game.history import EventType
    
    # Clear module cache to ensure fresh bot loading
    import sys
    module_keys = [k for k in list(sys.modules.keys()) if 'mossad_bot' in k.lower()]
    for key in module_keys:
        del sys.modules[key]
    
    # Import bot classes
    from bots.mossad_bot_advanced import MossadBotAdvanced
    
    # Create engine
    engine = GameEngine(seed=seed, quiet_mode=True, chat_enabled=False, bot_timeout=None)
    
    # Create hero with custom weights
    hero = MossadBotAdvanced(weights=hero_weights)
    engine.add_bot(hero)
    
    # Load random bots
    loader = BotLoader()
    project_root = Path(__file__).parent.parent
    random_bots = loader.load_from_file(project_root / "bots" / "random_bot.py")
    if random_bots:
        random_bot_class = type(random_bots[0])
        for i in range(4):
            engine.add_bot(random_bot_class())
    
    # Load deck
    deck_config = project_root / "configs" / "default_deck.json"
    if deck_config.exists():
        deck = engine.registry.create_deck_from_file(deck_config)
        engine._state._draw_pile = deck
        engine._rng.shuffle(engine._state._draw_pile)
    
    # Get hero ID
    hero_id = None
    for pid in engine._bots.keys():
        if pid.startswith("MossadBotAdvanced"):
            hero_id = pid
            break
    
    # Run game
    winner = engine.run()
    
    # Extract elimination order
    elimination_order: list[str] = []
    for event in engine.history.get_events():
        if event.event_type == EventType.PLAYER_ELIMINATED:
            if event.player_id:
                elimination_order.append(event.player_id)
    
    # Calculate placement
    placements = [winner] + list(reversed(elimination_order)) if winner else []
    
    hero_won = winner == hero_id
    hero_placement = 5
    if hero_id:
        if hero_won:
            hero_placement = 1
        elif hero_id in placements:
            hero_placement = placements.index(hero_id) + 1
    
    return {
        "won": hero_won,
        "placement": hero_placement,
        "seed": seed,
    }


class GameSimulator:
    """
    High-performance game simulation engine.
    
    Uses parallel processing to run multiple games efficiently.
    """
    
    def __init__(self, max_workers: int | None = None) -> None:
        """
        Initialize the simulator.
        
        Args:
            max_workers: Maximum number of parallel workers. Defaults to CPU count.
        """
        self.max_workers = max_workers
    
    def run_batch(
        self,
        hero_weights: dict[str, float],
        batch_size: int = 100,
        base_seed: int = 42,
        show_progress: bool = True,
    ) -> float:
        """
        Run a batch of games and return the win rate.
        
        Args:
            hero_weights: Weight dictionary for the hero bot.
            batch_size: Number of games to run.
            base_seed: Base seed for game randomization.
            show_progress: Whether to show progress dots.
        
        Returns:
            Win rate as a float between 0.0 and 1.0.
        """
        # Prepare game arguments
        game_args = [
            (hero_weights, (base_seed + i * 1000) % (2**31))
            for i in range(batch_size)
        ]
        
        wins = 0
        completed = 0
        
        start_time = time.time()
        
        # Run games in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_run_single_game, args) for args in game_args]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    if result["won"]:
                        wins += 1
                    completed += 1
                    
                    if show_progress and completed % 10 == 0:
                        print(".", end="", flush=True)
                        
                except Exception:
                    completed += 1
        
        duration = time.time() - start_time
        win_rate = wins / max(1, completed)
        
        if show_progress:
            print(f" ({duration:.1f}s)")
        
        return win_rate
    
    def run_detailed_batch(
        self,
        hero_weights: dict[str, float],
        batch_size: int = 100,
        base_seed: int = 42,
    ) -> dict[str, Any]:
        """
        Run a batch of games and return detailed statistics.
        
        Args:
            hero_weights: Weight dictionary for the hero bot.
            batch_size: Number of games to run.
            base_seed: Base seed for game randomization.
        
        Returns:
            Dict with detailed statistics.
        """
        # Prepare game arguments
        game_args = [
            (hero_weights, (base_seed + i * 1000) % (2**31))
            for i in range(batch_size)
        ]
        
        results: list[dict[str, Any]] = []
        
        start_time = time.time()
        
        # Run games in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_run_single_game, args) for args in game_args]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception:
                    pass
        
        duration = time.time() - start_time
        
        # Calculate statistics
        wins = sum(1 for r in results if r["won"])
        placements = [r["placement"] for r in results]
        
        placement_dist: dict[int, int] = {}
        for p in placements:
            placement_dist[p] = placement_dist.get(p, 0) + 1
        
        return {
            "win_rate": wins / max(1, len(results)),
            "wins": wins,
            "games": len(results),
            "avg_placement": sum(placements) / max(1, len(placements)),
            "placement_distribution": placement_dist,
            "duration": duration,
        }


def run_batch(hero_weights: dict[str, float], batch_size: int = 100) -> float:
    """
    Convenience function to run a batch of games.
    
    Args:
        hero_weights: Weight dictionary for the hero bot.
        batch_size: Number of games to run.
    
    Returns:
        Win rate as a float between 0.0 and 1.0.
    """
    simulator = GameSimulator()
    return simulator.run_batch(hero_weights, batch_size, show_progress=False)


if __name__ == "__main__":
    # Test the simulator
    from bots.mossad_bot_advanced import DEFAULT_WEIGHTS
    
    print("🎮 Testing Game Simulator")
    print("=" * 50)
    print(f"Weights: {DEFAULT_WEIGHTS}")
    print()
    
    simulator = GameSimulator()
    
    print("Running 50 games", end="")
    stats = simulator.run_detailed_batch(DEFAULT_WEIGHTS, batch_size=50)
    
    print(f"\n📊 Results:")
    print(f"   Win Rate: {stats['win_rate']:.1%}")
    print(f"   Avg Placement: {stats['avg_placement']:.2f}")
    print(f"   Placement Distribution: {stats['placement_distribution']}")
    print(f"   Duration: {stats['duration']:.1f}s")
