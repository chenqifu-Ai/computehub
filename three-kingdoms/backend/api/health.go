package api

import (
	"encoding/json"
	"net/http"
)

func HealthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  "ok",
		"version": "0.1.0",
		"node":    "ecs-p2ph (小智)",
		"message": "端智ARM→ECS x86_64 数据链已通",
	})
}