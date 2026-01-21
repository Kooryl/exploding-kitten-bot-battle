"""
Bot Version Comparison Script

Compares the performance of two bot versions and automatically
rolls back if the new version is worse.

Usage:
    py mossad_advanced/compare_versions.py
"""

import shutil
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


def run_comparison(games: int = 500) -> dict[str, float]:
    """
    Run performance comparison between v6 (backup) and v7 (new).
    
    Returns dict with win rates for both versions.
    """
    import subprocess
    import re
    
    results: dict[str, float] = {}
    
    # Test v7 (current)
    print("=" * 70)
    print("Testing NEW version (v7)...")
    print("=" * 70)
    
    cmd = [
        "py", "-m", "game.main",
        "--bot", "bots/mossad_bot_advanced.py",
        "--bot", "bots/random_bot.py:4",
        "--stats",
        "--iterations", str(games),
        "--no-chat"
    ]
    
    env = {"PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(parent_dir),
        env={**dict(__import__("os").environ), **env}
    )
    
    # Parse win rate from output
    match = re.search(r"MossadBotAdvanced\s+\d+\s+([\d.]+)%", result.stdout)
    if match:
        results["v7_new"] = float(match.group(1))
        print(f"V7 (NEW) Win Rate: {results['v7_new']:.1f}%")
    else:
        print("ERROR: Could not parse v7 results")
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        results["v7_new"] = 0.0
    
    # Test v6 (backup)
    print()
    print("=" * 70)
    print("Testing OLD version (v6 backup)...")
    print("=" * 70)
    
    # Temporarily swap files
    current = parent_dir / "bots" / "mossad_bot_advanced.py"
    backup = parent_dir / "bots" / "mossad_bot_advanced_v6_backup.py"
    temp = parent_dir / "bots" / "mossad_bot_advanced_temp.py"
    
    if backup.exists():
        # Swap
        shutil.copy(current, temp)
        shutil.copy(backup, current)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(parent_dir),
            env={**dict(__import__("os").environ), **env}
        )
        
        # Parse win rate
        match = re.search(r"MossadBotAdvanced\s+\d+\s+([\d.]+)%", result.stdout)
        if match:
            results["v6_old"] = float(match.group(1))
            print(f"V6 (OLD) Win Rate: {results['v6_old']:.1f}%")
        else:
            print("ERROR: Could not parse v6 results")
            results["v6_old"] = 0.0
        
        # Restore v7
        shutil.copy(temp, current)
        temp.unlink()
    else:
        print("WARNING: No v6 backup found")
        results["v6_old"] = 0.0
    
    return results


def main() -> None:
    """Main comparison and rollback logic."""
    import json
    from datetime import datetime
    
    print("=" * 70)
    print("BOT VERSION COMPARISON")
    print("=" * 70)
    print()
    
    # Run comparison
    results = run_comparison(games=500)
    
    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    v7 = results.get("v7_new", 0.0)
    v6 = results.get("v6_old", 0.0)
    
    print(f"V6 (OLD): {v6:.1f}%")
    print(f"V7 (NEW): {v7:.1f}%")
    print(f"Difference: {v7 - v6:+.1f}%")
    print()
    
    # Decision
    if v7 >= v6:
        print("✅ NEW VERSION IS EQUAL OR BETTER - Keeping v7")
        decision = "keep_v7"
    else:
        print("❌ NEW VERSION IS WORSE - Rolling back to v6")
        decision = "rollback_v6"
        
        # Perform rollback
        current = Path(__file__).parent.parent / "bots" / "mossad_bot_advanced.py"
        backup = Path(__file__).parent.parent / "bots" / "mossad_bot_advanced_v6_backup.py"
        
        if backup.exists():
            shutil.copy(backup, current)
            print("   Rollback complete!")
        else:
            print("   WARNING: Could not rollback - backup not found")
    
    # Log results
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "v6_win_rate": v6,
        "v7_win_rate": v7,
        "difference": v7 - v6,
        "decision": decision,
    }
    
    log_file = Path(__file__).parent / "version_comparison_log.json"
    
    # Load existing log
    if log_file.exists():
        with open(log_file) as f:
            log = json.load(f)
    else:
        log = []
    
    log.append(log_entry)
    
    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)
    
    print()
    print(f"Results logged to: {log_file}")


if __name__ == "__main__":
    main()
