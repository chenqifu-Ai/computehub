package main

import (
	"log"
	"net/http"

	"three-kingdoms/backend/api"
)

func main() {
	// 前端静态文件（含交流大厅）
	// 注意：binary 在 ~/three-kingdoms/，frontend/ 在同级目录
	fs := http.FileServer(http.Dir("frontend"))
	http.Handle("/", fs)
	http.HandleFunc("/chat", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "frontend/chat.html")
	})

	// API 端点 — 小智的后端 handlers
	http.HandleFunc("/api/health", api.Health)
	http.HandleFunc("/api/generals", api.GetGenerals)
	http.HandleFunc("/api/cities", api.GetCities)
	http.HandleFunc("/api/game/start", api.StartGame)
	http.HandleFunc("/api/game/", api.GameHandler)

	log.Println("========================================")
	log.Println("  🏯 三国策略游戏服务器 v0.1.0")
	log.Println("  📡 数据: 端智(ARM) → ECS(x86_64)")
	log.Println("  🖥️  后端: 小智(ECS) Go 引擎")
	log.Println("  🎨 前端: 端智(ARM) Canvas 地图")
	log.Println("  监听 :8080 ...")
	log.Println("========================================")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal("服务器启动失败:", err)
	}
}