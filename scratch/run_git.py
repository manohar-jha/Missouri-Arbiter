import subprocess
import os

git_cmd = None
search_dirs = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expanduser("~")
]

for sdir in search_dirs:
    if os.path.exists(sdir):
        for root, dirs, files in os.walk(sdir):
            if "git.exe" in files:
                git_cmd = os.path.join(root, "git.exe")
                break
        if git_cmd:
            break

print("FOUND GIT AT:", git_cmd)

def run_git(args):
    cmd = [git_cmd] + args
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=r"C:\Users\manoh\.antigravity-ide")
    print(f"--- GOT RETURNCODE {res.returncode} FOR: git {' '.join(args)} ---")
    if res.stdout:
        print("STDOUT:")
        print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)
    return res

if __name__ == "__main__":
    run_git(["status"])
    run_git(["branch"])
    run_git(["remote", "-v"])
    run_git(["log", "--oneline", "-n", "5"])
