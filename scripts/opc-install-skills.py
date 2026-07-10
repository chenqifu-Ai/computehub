import urllib.request
import os
import tarfile

dest = r"C:\opc-transfer"
os.makedirs(dest, exist_ok=True)

files = {
    "opc-skills-master.tar.gz": "http://36.250.122.43:8282/api/v1/download?file=opc-skills-master.tar.gz",
    "opc-sop-bundle.tar.gz": "http://36.250.122.43:8282/api/v1/download?file=opc-sop-bundle.tar.gz",
    "opc-knowledge-bundle.tar.gz": "http://36.250.122.43:8282/api/v1/download?file=opc-knowledge-bundle.tar.gz",
}

for name, url in files.items():
    path = os.path.join(dest, name)
    print(f"Downloading {name}...")
    urllib.request.urlretrieve(url, path)
    size = os.path.getsize(path)
    print(f"  -> {size} bytes OK")

# Extract
ws = os.path.expanduser(r"~\.openclaw\workspace\skills")
os.makedirs(ws, exist_ok=True)

for name in files:
    path = os.path.join(dest, name)
    print(f"Extracting {name}...")
    with tarfile.open(path, "r:gz") as tar:
        tar.extractall(dest)
    print(f"  Done")

# Move skills into place
import shutil
src_skills = os.path.join(dest, "skills-master", "package-skills")
src_ws = os.path.join(dest, "skills-master", "workspace-skills")
if os.path.isdir(src_skills):
    for d in os.listdir(src_skills):
        shutil.copytree(os.path.join(src_skills, d), os.path.join(ws, d), dirs_exist_ok=True)
if os.path.isdir(src_ws):
    for d in os.listdir(src_ws):
        shutil.copytree(os.path.join(src_ws, d), os.path.join(ws, d), dirs_exist_ok=True)

# Extract SOP to workspace root
wsroot = os.path.expanduser(r"~\.openclaw\workspace")
src_sop = os.path.join(dest, "sop-bundle")
if os.path.isdir(src_sop):
    for f in os.listdir(src_sop):
        src = os.path.join(src_sop, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(wsroot, f))

# Extract knowledge
src_know = os.path.join(dest, "knowledge-bundle")
if os.path.isdir(src_know):
    topics_src = os.path.join(src_know, "topics")
    if os.path.isdir(topics_src):
        topics_dst = os.path.join(wsroot, "memory", "topics")
        os.makedirs(topics_dst, exist_ok=True)
        shutil.copytree(topics_src, topics_dst, dirs_exist_ok=True)
    scripts_src = os.path.join(src_know, "scripts")
    if os.path.isdir(scripts_src):
        scripts_dst = os.path.join(wsroot, "scripts")
        os.makedirs(scripts_dst, exist_ok=True)
        for f in os.listdir(scripts_src):
            shutil.copy2(os.path.join(scripts_src, f), os.path.join(scripts_dst, f))
    for f in ["MEMORY.md", "IDENTITY.md", "TOOLS.md", "USER.md", "HEARTBEAT.md"]:
        src = os.path.join(src_know, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(wsroot, f))

print("\n=== ALL DONE ===")
skills_count = len(os.listdir(ws)) if os.path.isdir(ws) else 0
print(f"Skills installed: {skills_count}")
print(f"Workspace: {wsroot}")
