#!/bin/bash
# Daily update script for web-automation skill
# Syncs from upstream sources

SKILL_DIR="/root/.openclaw/workspace/skills/web-automation"
LOG_FILE="/root/.openclaw/workspace/skills/web-automation/update.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting update..." >> "$LOG_FILE"

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Update page-agent reference
echo "Updating page-agent..." >> "$LOG_FILE"
curl -sL "https://raw.githubusercontent.com/nicepkg/page-agent/main/README.md" > page-agent-readme.md 2>> "$LOG_FILE"

# Update browser-automation skill
echo "Updating browser-automation skill..." >> "$LOG_FILE"
git clone --depth 1 https://github.com/nardwang2026/openclaw-browser-automation-skill.git 2>> "$LOG_FILE"

if [ -d "openclaw-browser-automation-skill" ]; then
    # Copy updated scripts
    cp -r openclaw-browser-automation-skill/scripts/* "$SKILL_DIR/scripts/" 2>> "$LOG_FILE"
    cp -r openclaw-browser-automation-skill/references/* "$SKILL_DIR/references/" 2>> "$LOG_FILE"
    echo "Scripts and references updated" >> "$LOG_FILE"
fi

# Update clawdbot-manus skill for advanced automation
echo "Updating manus skill..." >> "$LOG_FILE"
git clone --depth 1 https://github.com/mvanhorn/clawdbot-skill-manus.git 2>> "$LOG_FILE"

if [ -d "clawdbot-skill-manus" ]; then
    # Copy relevant automation references
    cp -r clawdbot-skill-manus/scripts/* "$SKILL_DIR/scripts/" 2>> "$LOG_FILE" || true
    echo "Manus skill references updated" >> "$LOG_FILE"
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Update completed" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"