#!/usr/bin/env python3
"""
红茶机器配置修复脚本
修复 ollama-cloud 端点和模型ID配置
"""

import json
import sys

def fix_redtea_config():
    """修复红茶机器配置"""
    
    # 读取当前配置
    try:
        with open('/home/chen/.openclaw/openclaw.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        return False
    
    print("🔧 开始修复红茶机器配置...")
    
    # 修复 ollama-cloud 配置
    if 'ollama-cloud' in config['models']['providers']:
        prov = config['models']['providers']['ollama-cloud']
        
        # 修复 baseUrl
        old_url = prov.get('baseUrl', '')
        prov['baseUrl'] = 'https://ollama.com/api'
        print(f"✅ 修复端点: {old_url} → {prov['baseUrl']}")
        
        # 修复模型 ID（添加 -cloud 后缀）
        fixed_count = 0
        for model in prov['models']:
            model_id = model['id']
            # 如果不是以 -cloud 结尾，添加后缀
            if not model_id.endswith('-cloud'):
                # 特殊处理已有 :cloud 后缀的
                if ':cloud' in model_id:
                    new_id = model_id.replace(':cloud', '-cloud')
                else:
                    new_id = model_id + '-cloud'
                print(f"✅ 修复模型ID: {model_id} → {new_id}")
                model['id'] = new_id
                fixed_count += 1
        
        print(f"✅ 修复完成，共修复 {fixed_count} 个模型ID")
    
    # 修复别名配置
    if 'agents' in config and 'defaults' in config['agents'] and 'models' in config['agents']['defaults']:
        models_dict = config['agents']['defaults']['models']
        new_models = {}
        fixed_aliases = 0
        
        for key, value in models_dict.items():
            if key.startswith('ollama-cloud/'):
                # 修复别名中的模型 ID
                model_id = key.split('/')[1]
                if not model_id.endswith('-cloud'):
                    if ':cloud' in model_id:
                        new_key = key.replace(':cloud', '-cloud')
                    else:
                        new_key = key + '-cloud'
                    print(f"✅ 修复别名: {key} → {new_key}")
                    new_models[new_key] = value
                    fixed_aliases += 1
                else:
                    new_models[key] = value
            else:
                new_models[key] = value
        
        config['agents']['defaults']['models'] = new_models
        print(f"✅ 别名修复完成，共修复 {fixed_aliases} 个别名")
    
    # 保存配置
    try:
        with open('/home/chen/.openclaw/openclaw.json', 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("✅ 配置已保存")
        return True
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False

if __name__ == "__main__":
    success = fix_redtea_config()
    sys.exit(0 if success else 1)