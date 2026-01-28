# Run Mossad Bot Warfare vs 4 MossadBotAdvanced bots
# 2000 iterations

$env:PYTHONIOENCODING="utf-8"
py -m game.main --stats --bot bots/mossad_bot_warfare.py --bot bots/mossad_bot_advanced.py:4 --iterations 2000 --no-chat
