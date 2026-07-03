// Package agent — Hall 消息路由
// Phase 3: 将 Hall 消息路由到对应的专家 Agent
//
// 路由规则:
// 1. @专家名 → 直接路由到该专家
// 2. 内容匹配专家标签 → 自动触发专家参与
// 3. 复杂任务 → 小智分解后委派给专家

package agent

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"image"
	"image/jpeg"
	_ "image/png"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

// gatewayBaseURL 用于下载附件（由 SetGatewayURL 设置）
var gatewayBaseURL = "http://127.0.0.1:8282"

// SetGatewayURL 设置 Gateway 基础 URL（供附件下载用）
func SetGatewayURL(url string) {
	gatewayBaseURL = url
}

// ══════════════════════════════════════════════════════════════════════
//  HallRouter 定义
// ══════════════════════════════════════════════════════════════════════

// HallRouter Hall 消息路由器
type HallRouter struct {
	registry *ExpertRegistry
	agent    *Agent
	mu       sync.RWMutex

	// 回调：发送消息到 Hall
	postMessage func(topic, from, fromName, to, content string)

	// 活跃会话
	sessions map[string]*HallSession
}

// HallSession Hall 会话
type HallSession struct {
	Topic     string
	Initiator string // 发起人
	CreatedAt time.Time
	Messages  []HallMessage
}

// HallMessage Hall 消息
type HallMessage struct {
	From    string
	Content string
	Time    time.Time
}

// Attachment 文件附件
type Attachment struct {
	Name string `json:"name"`
	URL  string `json:"url"`
	Size int64  `json:"size"`
	Type string `json:"type"`
}

// NewHallRouter 创建 Hall 路由器
func NewHallRouter(registry *ExpertRegistry, agent *Agent) *HallRouter {
	return &HallRouter{
		registry:  registry,
		agent:     agent,
		sessions:  make(map[string]*HallSession),
	}
}

// SetPostMessage 设置发送消息到 Hall 的回调
func (hr *HallRouter) SetPostMessage(fn func(topic, from, fromName, to, content string)) {
	hr.postMessage = fn
}

// PostMessage 发送消息到 Hall
func (hr *HallRouter) PostMessage(topic, from, fromName, to, content string) {
	if hr.postMessage != nil {
		hr.postMessage(topic, from, fromName, to, content)
	}
}

// HandleMessage 处理一条 Hall 消息
// 返回 true 表示已处理（有专家回复）
func (hr *HallRouter) HandleMessage(topic, from, fromName, to, content string, attachments []Attachment) bool {
	// 不处理自己的消息
	if from == "小智" || fromName == "小智" {
		return false
	}

	// 不处理 join/leave 等系统消息
	if strings.Contains(content, "已加入大厅") || strings.Contains(content, "交流大厅 v2") {
		return false
	}

	// 不处理专家之间的互相 @（防止死循环）
	// 专家回复中可能 @ 其他专家，这会导致无限递归
	if hr.registry.Get(from) != nil {
		return false
	}

	// Step 1: 检查是否 @ 了某个专家
	if expert := hr.findMentionedExpert(content); expert != nil {
		go hr.routeToExpert(expert, topic, from, fromName, content, attachments)
		return true
	}

	// Step 2: 检查内容是否匹配专家标签（自动参与）
	experts := hr.registry.MatchByContent(content)
	if len(experts) > 0 {
		for _, expert := range experts {
			go hr.routeToExpert(expert, topic, from, fromName, content, attachments)
		}
		return true
	}

	return false
}

// findMentionedExpert 查找消息中 @ 的专家
func (hr *HallRouter) findMentionedExpert(content string) *Expert {
	// 提取所有 @xxx
	parts := strings.Split(content, "@")
	for _, part := range parts[1:] { // 跳过第一个（@ 前的部分）
		// 取到空格或标点为止
		name := strings.TrimSpace(part)
		end := strings.IndexAny(name, " ,。！？\n\t")
		if end > 0 {
			name = name[:end]
		}
		if expert := hr.registry.GetByName(name); expert != nil {
			return expert
		}
	}
	return nil
}

// routeToExpert 将消息路由到专家
func (hr *HallRouter) routeToExpert(expert *Expert, topic, from, fromName, content string, attachments []Attachment) {
	// 提取问题（去掉 @专家名 部分）
	question := strings.TrimSpace(content)
	for _, name := range []string{"@" + expert.Nickname, "@" + expert.Name} {
		question = strings.ReplaceAll(question, name, "")
	}
	question = strings.TrimSpace(question)
	if question == "" {
		question = content
	}

	// 下载并读取附件内容
	attachmentsInfo := ""
	var imageDataURL string // 如果有图片，存第一张的 base64 数据
	if len(attachments) > 0 {
		var parts []string
		for _, att := range attachments {
			// 下载文件内容
			fileContent := downloadFileContent(att.URL)
			fileInfo := fmt.Sprintf("- %s (%s, %d bytes)", att.Name, att.Type, att.Size)

			// 检测是否为图片（MIME 类型以 image/ 开头，且内容为纯 base64）
			if strings.HasPrefix(att.Type, "image/") && len(fileContent) > 200 {
				if imageDataURL == "" {
					imageDataURL = fileContent
				}
				fileInfo += fmt.Sprintf("\n  [图片已嵌入，base64 数据长度: %d 字符]", len(fileContent))
			} else if fileContent != "" {
				// 截取前 8000 字符
				truncated := fileContent
				if len([]rune(truncated)) > 8000 {
					truncated = string([]rune(truncated)[:8000]) + "\n...（内容过长，已截断）"
				}
				fileInfo += fmt.Sprintf("\n  文件内容:\n%s", truncated)
			} else {
				fileInfo += "（无法读取文件内容）"
			}
			parts = append(parts, fileInfo)
		}
		attachmentsInfo = fmt.Sprintf("\n\n用户上传了以下文件附件：\n%s\n\n请根据文件内容回答用户的问题。", strings.Join(parts, "\n\n"))
	}

	// 构建专家提示（图片 base64 直接嵌入文本）
	task := fmt.Sprintf(`用户 @%s 在交流大厅问了一个问题，需要你回答。

用户问题: %s%s

请根据你的专业知识回答。回答要专业、简洁、有条理。`, fromName, question, attachmentsInfo)

	// 如果有图片，把 base64 数据直接拼在提示词末尾
	if imageDataURL != "" {
		task += fmt.Sprintf("\n\n以下是用户上传的图片（base64 编码），请分析图片内容：\n%s", imageDataURL)
	}

	// 专家思考
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	result, err := expert.Think(ctx, task, "hall-"+topic)
	if err != nil {
		errMsg := fmt.Sprintf("@%s 思考时遇到问题: %v", expert.Nickname, err)
		hr.PostMessage(topic, expert.ID, expert.Name, "all", errMsg)
		return
	}

	// 回复到 Hall
	reply := fmt.Sprintf("@%s %s", fromName, result)
	hr.PostMessage(topic, expert.ID, expert.Name, "all", reply)
}

// ══════════════════════════════════════════════════════════════════════
//  hall_speak 工具（Agent 用）
// ══════════════════════════════════════════════════════════════════════

// RegisterHallTools 在工具注册表中注册 Hall 相关工具
func RegisterHallTools(tr *ToolRegistry, router *HallRouter) {
	// hall_speak — 在 Hall 中发言
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "hall_speak",
			Description: "在交流大厅（AI Hall）中发言，可以 @ 其他 Agent 委派任务。使用格式：@目标Agent 任务描述",
			Parameters: []Param{
				{Name: "content", Type: "string", Required: true, Description: "发言内容，可以 @ 其他 Agent"},
				{Name: "topic", Type: "string", Required: false, Description: "话题（默认 general）"},
				{Name: "to", Type: "string", Required: false, Description: "接收者（默认 all）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			content, _ := args["content"].(string)
			if content == "" {
				return "", fmt.Errorf("content is required")
			}
			topic, _ := args["topic"].(string)
			if topic == "" {
				topic = "general"
			}
			to, _ := args["to"].(string)
			if to == "" {
				to = "all"
			}

			router.PostMessage(topic, "小智", "小智", to, content)

			// 如果 @ 了专家，等待专家回复
			if expert := router.findMentionedExpert(content); expert != nil {
				return fmt.Sprintf("已通过 Hall 向 @%s 委派任务，等待回复中...", expert.Nickname), nil
			}

			return "消息已发送到交流大厅", nil
		},
	})

	// hall_list_experts — 列出可用专家
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "hall_list_experts",
			Description: "列出交流大厅中可用的专家 Agent",
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			return router.registry.ListDescriptions(), nil
		},
	})

	// sessions_send — 跨 Agent 直连通信
	// 通过 Gateway API 直接向指定节点 Agent 发送消息并等待回复
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "sessions_send",
			Description: "向指定节点 Agent 发送消息并等待回复。用于跨节点协作、委派任务、查询状态。比 hall_speak 更直接，不经过 Hall 广播。",
			Parameters: []Param{
				{Name: "to", Type: "string", Required: true, Description: "目标节点 ID（如 ecs-p2ph, local-arm, windows-mobile）"},
				{Name: "message", Type: "string", Required: true, Description: "发送的消息内容"},
				{Name: "timeout", Type: "number", Required: false, Description: "等待回复超时秒数（默认 30）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			to, _ := args["to"].(string)
			message, _ := args["message"].(string)
			if to == "" || message == "" {
				return "", fmt.Errorf("to and message are required")
			}

			timeout := 30
			if t, ok := args["timeout"].(float64); ok && t > 0 {
				timeout = int(t)
			}

			// 通过 Gateway API 发送 direct_message
			apiURL := gatewayBaseURL + "/api/v1/agent/send"
			payload := map[string]string{
				"to":      to,
				"message": message,
				"from":    "小智",
			}
			body, _ := json.Marshal(payload)

			client := &http.Client{Timeout: time.Duration(timeout) * time.Second}
			resp, err := client.Post(apiURL, "application/json", bytes.NewReader(body))
			if err != nil {
				return "", fmt.Errorf("发送失败: %w", err)
			}
			defer resp.Body.Close()

			var result struct {
				Success bool `json:"success"`
				Data    struct {
					MsgID      string `json:"msg_id"`
					Sent       bool   `json:"sent"`
					NodeOnline bool   `json:"node_online"`
				} `json:"data"`
			}
			if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
				return "", fmt.Errorf("解析响应失败: %w", err)
			}

			if !result.Success {
				return "", fmt.Errorf("Gateway 返回错误")
			}

			if !result.Data.NodeOnline {
				return fmt.Sprintf("⚠️ 节点 %s 当前离线，消息已缓存，上线后自动投递。消息ID: %s", to, result.Data.MsgID), nil
			}

			// 轮询等待回复
			msgID := result.Data.MsgID
			pollURL := fmt.Sprintf("%s/api/v1/agent/send/result?msg_id=%s", gatewayBaseURL, msgID)
			pollClient := &http.Client{Timeout: 5 * time.Second}
			deadline := time.Now().Add(time.Duration(timeout) * time.Second)

			for time.Now().Before(deadline) {
				select {
				case <-ctx.Done():
					return "", ctx.Err()
				default:
				}

				time.Sleep(500 * time.Millisecond)

				pollResp, err := pollClient.Get(pollURL)
				if err != nil {
					continue
				}

				var pollResult struct {
					Success bool `json:"success"`
					Data    *struct {
						MsgID   string `json:"msg_id"`
						From    string `json:"from"`
						Content string `json:"content"`
					} `json:"data"`
				}
				if err := json.NewDecoder(pollResp.Body).Decode(&pollResult); err != nil {
					pollResp.Body.Close()
					continue
				}
				pollResp.Body.Close()

				if pollResult.Success && pollResult.Data != nil {
					return fmt.Sprintf("✅ %s 回复: %s", to, pollResult.Data.Content), nil
				}
			}

			return fmt.Sprintf("⏳ 已发送至 %s，但未在 %d 秒内收到回复。消息ID: %s（可通过 /api/v1/agent/send/result?msg_id=%s 查询）",
				to, timeout, msgID, msgID), nil
		},
	})
}

// downloadFileContent 下载文件内容并返回文本
// 支持 .txt/.docx/.py/.go/.js/.json/.md 等文本文件
// 图片文件返回描述信息
func downloadFileContent(url string) string {
	if url == "" {
		return ""
	}

	// 构造完整 URL
	fullURL := url
	if strings.HasPrefix(url, "/") {
		fullURL = gatewayBaseURL + url
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(fullURL)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	// 读取内容（限制 1MB）
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return ""
	}

	// 检测是否为文本内容
	contentType := resp.Header.Get("Content-Type")

	// .docx 文件：解压 ZIP 并提取 word/document.xml 中的文本
	if strings.Contains(contentType, "officedocument") || strings.Contains(contentType, "msword") {
		return extractDocxText(body)
	}

	if strings.HasPrefix(contentType, "text/") ||
		strings.Contains(contentType, "json") ||
		strings.Contains(contentType, "javascript") ||
		strings.Contains(contentType, "x-python") ||
		strings.Contains(contentType, "x-go") {
		return string(body)
	}

	// 图片文件 → base64 编码嵌入提示词（自动压缩到 200KB 以内）
	// 返回纯 base64 字符串，不含 data:image/ 前缀（避免触发 API vision 路由）
	if strings.HasPrefix(contentType, "image/") {
		return compressAndEncodeImage(body, contentType)
	}

	// 二进制文件
	return fmt.Sprintf("[二进制文件: %s, %d bytes]", contentType, len(body))
}

// compressAndEncodeImage 压缩图片到 200KB 以内并 base64 编码
func compressAndEncodeImage(data []byte, contentType string) string {
	// 解码图片
	img, _, err := image.Decode(bytes.NewReader(data))
	if err != nil {
		return fmt.Sprintf("[图片解码失败: %v]", err)
	}

	bounds := img.Bounds()
	w := bounds.Dx()
	h := bounds.Dy()

	// 从 85% 质量开始，逐步降低直到 < 200KB
	quality := 85
	var encoded string
	for quality >= 10 {
		var buf bytes.Buffer
		switch contentType {
		case "image/png":
			// PNG 转 JPEG 压缩
			err = jpeg.Encode(&buf, img, &jpeg.Options{Quality: quality})
		default:
			err = jpeg.Encode(&buf, img, &jpeg.Options{Quality: quality})
		}
		if err != nil {
			return fmt.Sprintf("[图片压缩失败: %v]", err)
		}

		compressed := buf.Bytes()
		// 如果压缩后还太大，缩小尺寸
		if len(compressed) > 180*1024 {
			// 缩小到 75%
			newW := w * 75 / 100
			newH := h * 75 / 100
			if newW < 100 || newH < 100 {
				break
			}
			// 用 JPEG 质量降低 + 缩小尺寸
			quality -= 15
			w = newW
			h = newH
			continue
		}

		encoded = base64.StdEncoding.EncodeToString(compressed)
		if len(encoded) < 200*1024 { // base64 后 < 200KB
			return encoded
		}
		quality -= 15
	}

	// 如果压缩到最低质量还是太大，缩小尺寸再试
	scale := 50
	for scale >= 20 {
		newW := bounds.Dx() * scale / 100
		newH := bounds.Dy() * scale / 100
		if newW < 50 || newH < 50 {
			break
		}

		// 用 nearest neighbor 缩放到目标尺寸
		scaled := resizeImage(img, newW, newH)
		var buf bytes.Buffer
		jpeg.Encode(&buf, scaled, &jpeg.Options{Quality: 30})
		compressed := buf.Bytes()
		encoded = base64.StdEncoding.EncodeToString(compressed)
		if len(encoded) < 200*1024 {
			return encoded
		}
		scale -= 10
	}

	return fmt.Sprintf("[图片文件: %dx%d, %d bytes — 压缩后仍超过限制]", bounds.Dx(), bounds.Dy(), len(data))
}

// resizeImage 使用 nearest neighbor 缩放图片
func resizeImage(img image.Image, newW, newH int) image.Image {
	src := img.Bounds()
	dst := image.NewRGBA(image.Rect(0, 0, newW, newH))
	for y := 0; y < newH; y++ {
		for x := 0; x < newW; x++ {
			sx := x * src.Dx() / newW
			sy := y * src.Dy() / newH
			dst.Set(x, y, img.At(sx, sy))
		}
	}
	return dst
}

// extractDocxText 从 .docx (ZIP) 文件中提取纯文本
func extractDocxText(data []byte) string {
	reader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return fmt.Sprintf("[无法解压 docx 文件: %v]", err)
	}

	// 查找 word/document.xml
	for _, f := range reader.File {
		if f.Name == "word/document.xml" {
			rc, err := f.Open()
			if err != nil {
				return fmt.Sprintf("[无法读取 docx 内容: %v]", err)
			}
			defer rc.Close()

			xmlData, err := io.ReadAll(rc)
			if err != nil {
				return fmt.Sprintf("[读取 docx 内容失败: %v]", err)
			}

			return extractTextFromDocxXML(xmlData)
		}
	}

	return "[docx 文件中未找到 word/document.xml]"
}

// extractTextFromDocxXML 从 docx 的 XML 中提取纯文本
func extractTextFromDocxXML(xmlData []byte) string {
	// 定义 XML 结构
	type T struct {
		Text string `xml:",chardata"`
	}
	type R struct {
		T T `xml:"t"`
	}
	type P struct {
		R []R `xml:"r"`
	}
	type Body struct {
		P []P `xml:"p"`
	}

	var doc struct {
		Body Body `xml:"body"`
	}

	if err := xml.Unmarshal(xmlData, &doc); err != nil {
		return fmt.Sprintf("[解析 docx XML 失败: %v]", err)
	}

	var paragraphs []string
	for _, p := range doc.Body.P {
		var line string
		for _, r := range p.R {
			line += r.T.Text
		}
		paragraphs = append(paragraphs, line)
	}

	return strings.Join(paragraphs, "\n")
}
