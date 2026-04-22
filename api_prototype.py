import sqlite3
import os
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "/root/.openclaw/workspace/ai_agent/results/computehub_local.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/nodes/register', methods=['POST'])
def register_node():
    data = request.json
    if not data: return jsonify({"error": "Missing request body"}), 400
    node_id = data.get('node_id', 'unknown')
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO nodes (node_id, hostname, ip_address, gpu_model, vram_total, status, last_heartbeat, region, created_at) VALUES (?, ?, ?, ?, ?, 'online', ?, ?, ?)", 
                       (node_id, data.get('hostname'), data.get('ip_address'), data.get('gpu_model'), data.get('vram_total'), datetime.now().isoformat(), data.get('region'), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "node_id": node_id}), 201
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/nodes/heartbeat', methods=['POST'])
def node_heartbeat():
    data = request.json
    node_id = data.get('node_id')
    if not node_id: return jsonify({"error": "Missing node_id"}), 400
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE nodes SET status = 'online', last_heartbeat = ? WHERE node_id = ?", (datetime.now().isoformat(), node_id))
        cursor.execute("INSERT INTO heartbeats (node_id, gpu_temp, gpu_util, vram_used, timestamp) VALUES (?, ?, ?, ?, ?)", 
                       (node_id, data.get('gpu_temp'), data.get('gpu_util'), data.get('vram_used'), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/nodes/status', methods=['GET'])
def get_nodes_status():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes")
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"total_nodes": len(rows), "online_nodes": len([r for r in rows if r['status'] == 'online']), "nodes": [dict(r) for r in rows]}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

# 关键修改：支持 /computehub 前缀
@app.route('/computehub/nodes/status', methods=['GET'])
def get_nodes_status_hub():
    return get_nodes_status()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
