import os, shutil

# Source: where files were installed (SYSTEM profile)
src_root = os.path.join("C:\\Windows", "system32", "config", "systemprofile", ".openclaw", "workspace")

# Target: Administrator's OpenClaw workspace
dst_root = os.path.join("C:\\Users", "Administrator", ".openclaw")

# Also check if there's a workspace subdir
for check in [dst_root, os.path.join(dst_root, "workspace")]:
    if os.path.isdir(check):
        print(f"Found: {check}")

print(f"\nSource: {src_root}")
print(f"Target: {dst_root}")
print(f"Source exists: {os.path.isdir(src_root)}")
print(f"Target exists: {os.path.isdir(dst_root)}")

# List what's in source
if os.path.isdir(src_root):
    items = os.listdir(src_root)
    print(f"\nSource contents ({len(items)} items):")
    for i in items[:20]:
        p = os.path.join(src_root, i)
        t = "DIR" if os.path.isdir(p) else "FILE"
        print(f"  [{t}] {i}")

# Copy skills
src_skills = os.path.join(src_root, "skills")
dst_skills = os.path.join(dst_root, "skills")
if os.path.isdir(src_skills):
    os.makedirs(dst_skills, exist_ok=True)
    count = 0
    for item in os.listdir(src_skills):
        s = os.path.join(src_skills, item)
        d = os.path.join(dst_skills, item)
        try:
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
                count += 1
            else:
                shutil.copy2(s, d)
                count += 1
        except Exception as e:
            print(f"  Skip {item}: {e}")
    print(f"\nSkills copied: {count}")

# Copy memory/topics
src_topics = os.path.join(src_root, "memory", "topics")
dst_topics = os.path.join(dst_root, "memory", "topics")
if os.path.isdir(src_topics):
    os.makedirs(dst_topics, exist_ok=True)
    shutil.copytree(src_topics, dst_topics, dirs_exist_ok=True)
    print("Memory topics copied!")

# Copy scripts
src_scripts = os.path.join(src_root, "scripts")
dst_scripts = os.path.join(dst_root, "scripts")
if os.path.isdir(src_scripts):
    os.makedirs(dst_scripts, exist_ok=True)
    for f in os.listdir(src_scripts):
        shutil.copy2(os.path.join(src_scripts, f), os.path.join(dst_scripts, f))
    print(f"Scripts copied: {len(os.listdir(src_scripts))}")

# Copy root .md files
for f in ["SOP.md", "AGENTS.md", "SOUL.md", "MEMORY.md", "IDENTITY.md", "TOOLS.md", "USER.md", "HEARTBEAT.md"]:
    s = os.path.join(src_root, f)
    if os.path.isfile(s):
        shutil.copy2(s, os.path.join(dst_root, f))
        print(f"Root: {f}")

# Verify
print("\n=== VERIFICATION ===")
if os.path.isdir(dst_skills):
    skill_dirs = len([d for d in os.listdir(dst_skills) if os.path.isdir(os.path.join(dst_skills, d))])
    skill_files = len([f for f in os.listdir(dst_skills) if os.path.isfile(os.path.join(dst_skills, f))])
    print(f"Skills: {skill_dirs} dirs, {skill_files} files")

if os.path.isdir(dst_topics):
    print(f"Topics: {len(os.listdir(dst_topics))} items")

if os.path.isdir(dst_scripts):
    print(f"Scripts: {len(os.listdir(dst_scripts))} files")

for f in ["SOP.md", "MEMORY.md"]:
    if os.path.isfile(os.path.join(dst_root, f)):
        print(f"{f}: OK")
    else:
        print(f"{f}: MISSING")

print("\n=== DONE ===")
