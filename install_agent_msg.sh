#!/bin/bash

# 创建 agent_msg.py 工具脚本
cat > /usr/local/bin/agent_msg.py << 'EOF'
#!/usr/bin/env python3
import sys
import os

def main():
    if len(sys.argv) < 3:
        print("Usage: agent_msg <node_name> <message>")
        sys.exit(1)
    
    node_name = sys.argv[1]
    message = " ".join(sys.argv[2:])
    
    # 这里可以添加实际的节点间通信逻辑
    print(f"Message to {node_name}: {message}")
    
    # 模拟发送成功
    print(f"✓ Message sent to {node_name}")

if __name__ == "__main__":
    main()
EOF

# 设置执行权限
chmod +x /usr/local/bin/agent_msg.py

# 创建软链接
ln -sf /usr/local/bin/agent_msg.py /usr/local/bin/agent_msg

# 添加到 bashrc
echo 'alias agent_msg="python3 /usr/local/bin/agent_msg.py"' >> ~/.bashrc

# 立即生效
source ~/.bashrc

echo "✓ agent_msg tool installed successfully"
echo "✓ You can now use: agent_msg <node> <message>"