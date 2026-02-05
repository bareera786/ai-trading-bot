# Check and fix the systemd service configuration
# Run these commands on the VPS

# 1. Check the current service file
sudo cat /etc/systemd/system/ai-trading-bot.service

# 2. Check recent service logs
sudo journalctl -u ai-trading-bot -n 100 --no-pager

# 3. Check if python3 is available
which python3

# 4. Check the working directory
ls -la /home/aibot/ai-bot/

# 5. Try to run the start command manually to see the error
cd /home/aibot/ai-bot && source venv/bin/activate && python3 run.py
