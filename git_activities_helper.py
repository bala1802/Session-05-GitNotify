import subprocess
import re
import datetime

def get_git_log():
    applescript = '''
    set repoPath to "/Users/apple/Desktop/Projects/Experiments/2025/EAG/Session-05/MCP-Repo/repository"
    set branchName to "main"
    set gitCommand to "cat " & quoted form of (repoPath & "/.git/logs/refs/heads/" & branchName)
    set gitOutput to do shell script gitCommand
    return gitOutput
    '''
    try:
        output = subprocess.check_output(['osascript', '-e', applescript])
        log = output.decode('utf-8')
        return log.strip()
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        return None