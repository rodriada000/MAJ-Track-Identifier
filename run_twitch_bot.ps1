# Powershell script to execute bot.py
# ... used to setup in Windows Task scheduler

# ensure vpn is not already running before starting bot
Get-Process "openvpn"  -ErrorAction SilentlyContinue | Stop-Process -ErrorAction SilentlyContinue

python .\bot.py
