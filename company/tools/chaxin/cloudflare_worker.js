// Cloudflare Worker - 茶信消息中转
// 部署到 Cloudflare Workers (免费额度：每天10万请求)

const API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii";

// KV存储（需要在Cloudflare创建KV命名空间）
// 绑定到 worker 的 KV namespace: CHAXIN_KV

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Authorization, Content-Type"
        }
      });
    }

    // 健康检查
    if (path === "/health") {
      return jsonResponse({ status: "ok", service: "chaxin-relay" });
    }

    // 认证检查
    const auth = request.headers.get("Authorization") || "";
    const keyParam = url.searchParams.get("key") || "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7) : keyParam;

    if (token !== API_KEY && !token.startsWith("node_")) {
      return jsonResponse({ error: "Unauthorized" }, 401);
    }

    // 节点注册
    if (path === "/node/register" && request.method === "POST") {
      const data = await request.json();
      const nodeId = data.id;
      const nodeData = {
        name: data.name || nodeId,
        endpoint: data.endpoint || "",
        last_seen: Date.now()
      };
      await env.CHAXIN_KV.put(`node:${nodeId}`, JSON.stringify(nodeData));
      return jsonResponse({ status: "registered", node_id: nodeId });
    }

    // 服务发现
    if (path === "/node/list") {
      const list = await env.CHAXIN_KV.list({ prefix: "node:" });
      const nodes = {};
      for (const key of list.keys) {
        const data = await env.CHAXIN_KV.get(key.name);
        if (data) {
          const nodeId = key.name.replace("node:", "");
          nodes[nodeId] = JSON.parse(data);
        }
      }
      return jsonResponse({ status: "ok", nodes });
    }

    // 发送消息
    if (path === "/msg/send" && request.method === "POST") {
      const data = await request.json();
      const recipient = data.to;
      if (!recipient) {
        return jsonResponse({ error: "Missing recipient" }, 400);
      }

      const msgId = `msg_${Date.now()}_${data.from || "unknown"}`;
      const msg = {
        id: msgId,
        from: data.from || "",
        to: recipient,
        subject: data.subject || "",
        body: data.body || "",
        priority: data.priority || "normal",
        timestamp: Date.now()
      };

      // 存储消息（保留24小时）
      const key = `msg:${recipient}:${msgId}`;
      await env.CHAXIN_KV.put(key, JSON.stringify(msg), { expirationTtl: 86400 });

      return jsonResponse({ status: "sent", msg_id: msgId });
    }

    // 接收消息
    if (path === "/msg/recv") {
      const recipient = url.searchParams.get("to");
      if (!recipient) {
        return jsonResponse({ error: "Missing recipient" }, 400);
      }

      const limit = parseInt(url.searchParams.get("limit") || "10");
      const list = await env.CHAXIN_KV.list({ prefix: `msg:${recipient}:`, limit });

      const messages = [];
      for (const key of list.keys) {
        const data = await env.CHAXIN_KV.get(key.name);
        if (data) {
          messages.push(JSON.parse(data));
          // 取出后删除
          await env.CHAXIN_KV.delete(key.name);
        }
      }

      return jsonResponse({ status: "ok", messages });
    }

    return jsonResponse({ error: "Not Found" }, 404);
  }
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    }
  });
}