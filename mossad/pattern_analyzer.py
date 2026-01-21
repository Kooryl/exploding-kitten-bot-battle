"""
Pattern Analyzer - Analyze game results for 5-player battle royale.
"""

from typing import Any


class PatternAnalyzer:
    """Analyze game logs to find failure patterns."""
    
    def analyze(self, test_results: dict[str, Any]) -> dict[str, Any]:
        """Analyzes game logs to find failure patterns."""
        games = test_results.get("games", [])
        losses = [g for g in games if not g.get("won", False)]
        
        if not losses:
            return {
                "primary_issue": "none",
                "rate_early_death": 0.0,
                "rate_hoarding_death": 0.0,
                "rate_starvation": 0.0,
            }
        
        analysis: dict[str, Any] = {
            "died_early": 0,         # Died in bottom 2 places (4th or 5th)
            "died_wasted_hand": 0,   # Died with many cards but no defuse
            "died_defuseless": 0,    # Died because ran out of defuse
            "died_late": 0,          # Died in 2nd or 3rd place (close!)
        }
        
        for game in losses:
            placement = game.get("placement", 5)
            final_defuses = game.get("final_defuse_count", 0)
            final_hand_size = game.get("final_hand_size", 0)
            
            # Died early (4th or 5th place)
            if placement >= 4:
                analysis["died_early"] += 1
            
            # Died late (2nd or 3rd place - close!)
            if placement in (2, 3):
                analysis["died_late"] += 1
            
            # Died without defuse
            if final_defuses == 0:
                analysis["died_defuseless"] += 1
            
            # Died with wasted hand (many cards but no defuse)
            if final_hand_size > 4 and final_defuses == 0:
                analysis["died_wasted_hand"] += 1
        
        total = len(losses)
        
        return {
            "rate_early_death": analysis["died_early"] / total,
            "rate_hoarding_death": analysis["died_wasted_hand"] / total,
            "rate_starvation": analysis["died_defuseless"] / total,
            "rate_late_death": analysis["died_late"] / total,
            "total_losses": total,
        }
