import os
import time
import json
import sys
import subprocess
import datetime
import asyncio
import random
import logging
from maj.utils import fileutils

DETACHED_PROCESS = 0x00000008

log = logging.getLogger(__name__)

# openvpn --config [Path\To\Config] --auth-user-pass [Path\To\userpwd.conf]'


class VpnRotator:
    def __init__(self, folder_paths, conf_path):
        self.folder_paths = folder_paths # list of folders where .ovpn files exist
        self.conf_path = conf_path # path to .conf file that has ovpn username/password
        self.files = [] # list of .ovpn files found based on folder_paths 
        self.used_files = [] # list of files recently connected to
        self.vpn_proc = None # current ovpn process
        self.is_connected = False

    def connect(self, ovpn_path):
        if self.is_connected is False:
            cmds = ["openvpn", "--config", ovpn_path, "--auth-user-pass", self.conf_path]
            logging.info(f"connecting to ... {' '.join(cmds)}")
            self.vpn_proc = subprocess.Popen(cmds, shell=False, stdin=None, stdout=None, stderr=None, close_fds=True, creationflags=DETACHED_PROCESS)
            self.is_connected = True


    def disconnect(self):
        if self.vpn_proc is not None:
            self.vpn_proc.kill()
            self.vpn_proc.wait()
            self.vpn_proc = None
            self.is_connected = False

    def get_all_files(self):
        self.files = []

        for folder in self.folder_paths:
            for file in fileutils.get_all_files(folder, recursive=True):
                if file.endswith(".ovpn"): 
                    self.files.append(os.path.join(folder, file))

    def connect_random(self):
        if len(self.used_files) >= len(self.files):
            # clear used list and get all files again
            self.used_files = []
            self.get_all_files()

        ovpn_file = self.files[random.randint(0, len(self.files) - 1)]
        while ovpn_file in self.used_files:
            ovpn_file = self.files[random.randint(0, len(self.files) - 1)]

        self.connect(ovpn_file)
        self.used_files.append(ovpn_file)



def demo_usage():
    v = VpnRotator(["C:\\Users\\Adica\\OpenVPN\\config"], "C:\\Users\\Adica\\OpenVPN\\config\\userpwd.conf")
    v.get_all_files()
    print(v.files)
    print(v.used_files)

    cmd = ""
    while cmd != "q":
        cmd = input("d = disconnect; q = quit; c = connect; s = status: ")

        if cmd == "d":
            v.disconnect()
        elif cmd == "s":
            print("is_connected: " + str(v.is_connected))
        elif cmd == "c":
            if v.is_connected:
                v.disconnect()
            v.connect_random()
            print(v.used_files)

    if v.is_connected:
        v.disconnect()

# if __name__ == "__main__":
#     demo_usage()