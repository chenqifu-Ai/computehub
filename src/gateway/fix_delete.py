import sys

with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

# Fix 1: Card delete button - use encodeURIComponent instead of escapeHtml
found = False
for i, line in enumerate(lines):
    if "confirmDelete(" in line and "escapeHtml(item.name)" in line:
        old = line
        new = line.replace("escapeHtml(item.name)", "encodeURIComponent(item.name)")
        lines[i] = new
        print(f"Line {i+1}: Fixed onclick escapeHtml -> encodeURIComponent")
        found = True
        break

if not found:
    print("WARNING: confirmDelete pattern with escapeHtml not found")
    # Search for alternatives
    for i, line in enumerate(lines):
        if 'confirmDelete' in line and 'onclick' in line:
            print(f"  Found on L{i+1}: {line.rstrip()}")

# Fix 2: Update confirmDelete function to decodeURIComponent
found2 = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("function confirmDelete("):
        # Add decodeURIComponent in the body
        for j in range(i, min(i+5, len(lines))):
            if "deleteTarget = name;" in lines[j] or "deleteTarget = encoded;" in lines[j]:
                lines[j] = lines[j].replace("deleteTarget = name;", "deleteTarget = decodeURIComponent(name);")
                lines[j] = lines[j].replace("deleteTarget = encoded;", "deleteTarget = decodeURIComponent(name);")
                print(f"Line {j+1}: Added decodeURIComponent")
                found2 = True
                break
        break

if not found2:
    print("WARNING: confirmDelete function not found")
    for i, line in enumerate(lines[:1450]):
        if 'function confirmDelete' in line:
            print(f"  Found at L{i+1}: {line.rstrip()}")

with open(sys.argv[1], 'w') as f:
    f.writelines(lines)

print("Done.")
