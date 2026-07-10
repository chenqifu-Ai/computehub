import os, tarfile, shutil

dest = "C:\\opc-transfer"
ws = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "skills")
wsroot = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace")
os.makedirs(ws, exist_ok=True)

def copy_tree_contents(src_dir, dst_dir):
    """Copy all items (dirs and files) from src to dst"""
    if not os.path.isdir(src_dir):
        return 0
    count = 0
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
            count += 1
        elif os.path.isfile(s):
            shutil.copy2(s, d)
            count += 1
    return count

# Skills
n = copy_tree_contents(os.path.join(dest, "skills-master", "package-skills"), ws)
print(f"Package skills: {n}")
n = copy_tree_contents(os.path.join(dest, "skills-master", "workspace-skills"), ws)
print(f"Workspace skills: {n}")

# SOP
sop_dir = os.path.join(dest, "sop-bundle")
if os.path.isdir(sop_dir):
    for f in os.listdir(sop_dir):
        src = os.path.join(sop_dir, f)
        if os.path.isfile(src) and f.endswith(".md"):
            shutil.copy2(src, os.path.join(wsroot, f))
            print(f"SOP: {f}")
    # Copy execution rules
    rules_src = os.path.join(sop_dir, "execution_rules")
    if os.path.isdir(rules_src):
        rules_dst = os.path.join(wsroot, "memory", "topics", "execution_rules")
        os.makedirs(rules_dst, exist_ok=True)
        shutil.copytree(rules_src, rules_dst, dirs_exist_ok=True)

# Knowledge base
know_dir = os.path.join(dest, "knowledge-bundle")
if os.path.isdir(know_dir):
    # Topics
    topics_src = os.path.join(know_dir, "topics")
    if os.path.isdir(topics_src):
        topics_dst = os.path.join(wsroot, "memory", "topics")
        os.makedirs(topics_dst, exist_ok=True)
        shutil.copytree(topics_src, topics_dst, dirs_exist_ok=True)
        print("Knowledge topics installed!")
    # Scripts
    scripts_src = os.path.join(know_dir, "scripts")
    if os.path.isdir(scripts_src):
        scripts_dst = os.path.join(wsroot, "scripts")
        os.makedirs(scripts_dst, exist_ok=True)
        for f in os.listdir(scripts_src):
            shutil.copy2(os.path.join(scripts_src, f), os.path.join(scripts_dst, f))
        print("Scripts installed!")
    # Root files
    for f in ["MEMORY.md", "IDENTITY.md", "TOOLS.md", "USER.md", "HEARTBEAT.md"]:
        src = os.path.join(know_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(wsroot, f))
            print(f"Root: {f}")

# Final count
skills_count = len([d for d in os.listdir(ws) if os.path.isdir(os.path.join(ws, d))])
files_count = len([f for f in os.listdir(ws) if os.path.isfile(os.path.join(ws, f))])
print(f"\n=== ALL DONE ===")
print(f"Skill directories: {skills_count}")
print(f"Skill files: {files_count}")
print(f"Workspace: {wsroot}")
