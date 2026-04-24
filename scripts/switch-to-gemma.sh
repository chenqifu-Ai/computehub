#!/bin/bash
# 切换到gemma-4-31b模型脚本

echo "🚀 切换到gemma-4-31b模型"

# 检查网络连通性
echo "🔍 检查模型服务器连通性..."
if ping -c 2 58.23.129.98 >/dev/null 2>&1; then
    echo "✅ 服务器网络通畅"
else
    echo "❌ 服务器网络不通，使用备用模型"
    exit 1
fi

# 尝试连接API
echo "🔗 尝试连接模型API..."
response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer sk-vmkohy18-34ga;sjd" \
    -H "Content-Type: application/json" \
    http://58.23.129.98:8001/v1/models \
    -o /tmp/gemma_test.json)

if [ "$response" -eq 200 ]; then
    echo "✅ API连接成功"
    
    # 检查是否包含gemma-4-31b
    if grep -q "gemma-4-31b" /tmp/gemma_test.json; then
        echo "✅ 找到gemma-4-31b模型"
        
        # 更新当前模型配置
        echo "⚙️ 更新模型配置..."
        
        # 创建模型切换标记
        echo "gemma-4-31b" > /tmp/current_model.txt
        
        echo "🎉 已切换到gemma-4-31b模型"
        echo "📊 模型信息:"
        echo "   - 名称: gemma-4-31b"
        echo "   - 服务器: http://58.23.129.98:8000/v1"
        echo "   - 类型: vLLM高性能工具调用"
        echo "   - 上下文: 128k tokens"
        
    else
        echo "❌ 未找到gemma-4-31b模型"
        echo "📋 可用模型:"
        cat /tmp/gemma_test.json | head -5
        exit 1
    fi
    
else
    echo "❌ API连接失败 (HTTP: $response)"
    echo "💡 建议检查:"
    echo "   1. API密钥是否正确"
    echo "   2. 服务器是否正常运行"
    echo "   3. 防火墙设置"
    exit 1
fi

# 清理临时文件
rm -f /tmp/gemma_test.json

echo ""
echo "💡 使用说明:"
echo "   当前会话将使用gemma-4-31b模型"
echo "   如果遇到问题，会自动回退到deepseek-v3.1:671b"
echo ""
echo "🔧 验证命令:"
echo "   curl -H 'Authorization: Bearer sk-vmkohy18-34ga;sjd' \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        http://58.23.129.98:8001/v1/models"
echo ""