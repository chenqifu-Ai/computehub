import requests
import os
import time

API_URL = "http://localhost:5000/nodes/status"

def clear_screen():
    os.system('clear')

def display_dashboard():
    try:
        resp = requests.get(API_URL)
        data = resp.json()
        
        clear_screen()
        print("="*60)
        print(f"🚀 ComputeHub 算力实时看板 | {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print(f"🌐 总节点数: {data['total_nodes']} | 🟢 在线节点: {data['online_nodes']}")
        print("-"*60)
        print(f"{'Node ID':<<115} | {'Model':<<115} | {'VRAM':<<88} | {'Region':<<110} | {'Status'}")
        print("-"*60)
        
        for node in data['nodes']:
            status_icon = "🟢" if node['status'] == 'online' else "🔴"
            print(f"{node['node_id']:<<115} | {node['gpu_model']:<<115} | {node['vram_total']:<<88} | {node['region']:<<110} | {status_icon} {node['status']}")
            
        print("="*60)
        print("💡 提示: 持续监控中... (Ctrl+C 退出)")
        
    except Exception as e:
        print(f"❌ 无法连接到 ComputeHub 服务: {e}")

if __name__ == "__main__":
    try:
        while True:
            display_dashboard()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n看板已关闭。")
