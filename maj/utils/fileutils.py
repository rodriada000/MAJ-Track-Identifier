import os
import sys
import datetime


def get_all_files(root, recursive=True):
    files = [ os.path.join(root, f) for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
    dirs = [ d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    
    if recursive:
        for d in dirs:
            files_in_d = get_all_files(os.path.join(root, d), True)

            if files_in_d:
                for f in files_in_d:
                    files.append(os.path.join(root, f))
    
    return files
