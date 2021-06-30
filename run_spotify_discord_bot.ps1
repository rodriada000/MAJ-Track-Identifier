# Powershell script to execute send_setlist.py
# ...creates spotify playlist based on todays setlist 
# ... and then uploads an image/message to the discord with the generated playlist.
# ... used to setup in Windows Task scheduler

# ensure source code is up-to-date before running
git pull

# ensure vpn is not connected before
Get-Process "openvpn" -ErrorAction SilentlyContinue | Stop-Process -ErrorAction SilentlyContinue

python .\send_setlist.py
