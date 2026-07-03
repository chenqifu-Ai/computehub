package gateway

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// OCRRequest represents an OCR API request
type OCRRequest struct {
	Image   string `json:"image"`   // base64 encoded image (JPEG/PNG)
	Lang    string `json:"lang"`    // tesseract lang string, default "chi_sim+eng"
	Timeout int    `json:"timeout"` // timeout in seconds, default 30
}

// OCRResponse represents an OCR API response
type OCRResponse struct {
	Text       string `json:"text"`
	Language   string `json:"language"`
	DurationMs int64  `json:"duration_ms"`
	Success    bool   `json:"success"`
}

// OCRStats represents OCR operation stats for monitoring
type OCRStats struct {
	TotalRuns  int64 `json:"total_runs"`
	TotalChars int64 `json:"total_chars"`
	AvgMs      int64 `json:"avg_ms"`
}

var ocrStats = OCRStats{}

// handleOCR handles POST /api/v1/ocr
func (g *OpcGateway) handleOCR(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		g.sendResponse(w, Response{Success: false, Error: "Only POST allowed"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var req OCRRequest
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.Image == "" {
		g.sendResponse(w, Response{Success: false, Error: "image (base64) is required"})
		return
	}

	if req.Lang == "" {
		req.Lang = "chi_sim+eng"
	}
	if req.Timeout <= 0 {
		req.Timeout = 30
	}

	// Decode base64 image
	imgData, err := base64.StdEncoding.DecodeString(req.Image)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Base64 decode failed: %v", err)})
		return
	}

	if len(imgData) == 0 {
		g.sendResponse(w, Response{Success: false, Error: "image data is empty"})
		return
	}

	// Verify tesseract is available
	if _, err := exec.LookPath("tesseract"); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "tesseract not installed: " + err.Error()})
		return
	}

	// Execute OCR with timeout
	start := time.Now()
	output, err := executeOCR(imgData, req.Lang, req.Timeout)
	duration := time.Since(start).Milliseconds()

	// Update stats
	ocrStats.TotalRuns++
	ocrStats.TotalChars += int64(len(output))
	if ocrStats.TotalRuns == 1 {
		ocrStats.AvgMs = duration
	} else {
		ocrStats.AvgMs = (ocrStats.AvgMs*(ocrStats.TotalRuns-1) + duration) / ocrStats.TotalRuns
	}

	if err != nil {
		g.sendResponse(w, Response{
			Success: false,
			Error:   fmt.Sprintf("OCR failed: %v", err),
		})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: OCRResponse{
			Text:       output,
			Language:   req.Lang,
			DurationMs: duration,
			Success:    true,
		},
	})
}

// executeOCR runs tesseract on image data and returns extracted text
func executeOCR(imgData []byte, lang string, timeoutSec int) (string, error) {
	// Create temp dir for this OCR operation
	tmpDir, err := os.MkdirTemp("", "computehub-ocr-")
	if err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	// Write image to temp file
	imgPath := filepath.Join(tmpDir, "input.jpg")
	if err := os.WriteFile(imgPath, imgData, 0644); err != nil {
		return "", fmt.Errorf("failed to write image: %w", err)
	}

	// Output file
	outPath := filepath.Join(tmpDir, "output")

	// Build tesseract command
	cmd := exec.Command("tesseract", imgPath, outPath, "-l", lang)

	// Set timeout
	if timeoutSec > 0 {
		timeout := time.Duration(timeoutSec) * time.Second
		done := make(chan struct{})
		var output bytes.Buffer
		cmd.Stdout = &output
		cmd.Stderr = &output

		go func() {
			cmd.Run()
			close(done)
		}()

		select {
		case <-done:
		case <-time.After(timeout):
			cmd.Process.Kill()
			return "", fmt.Errorf("OCR timeout after %ds: %s", timeoutSec, output.String())
		}
	} else {
		var output bytes.Buffer
		cmd.Stdout = &output
		cmd.Stderr = &output
		if err := cmd.Run(); err != nil {
			return "", fmt.Errorf("tesseract failed: %w: %s", err, output.String())
		}
	}

	// Read output
	result, err := os.ReadFile(outPath + ".txt")
	if err != nil {
		return "", fmt.Errorf("failed to read OCR result: %w", err)
	}

	// Clean up extra whitespace
	text := cleanOCRText(string(result))
	return text, nil
}

// cleanOCRText removes excessive whitespace and blank lines from OCR output
func cleanOCRText(text string) string {
	lines := bytes.Split([]byte(text), []byte("\n"))
	var cleaned bytes.Buffer
	prevBlank := false
	for _, line := range lines {
		trimmed := bytes.TrimSpace(line)
		if len(trimmed) == 0 {
			if !prevBlank {
				cleaned.WriteByte('\n')
			}
			prevBlank = true
		} else {
			cleaned.Write(trimmed)
			cleaned.WriteByte('\n')
			prevBlank = false
		}
	}
	return string(bytes.TrimSpace(cleaned.Bytes()))
}

// handleOCRStats returns OCR operation statistics
func (g *OpcGateway) handleOCRStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		g.sendResponse(w, Response{Success: false, Error: "Only GET allowed"})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: ocrStats,
	})
}

func init() {
	logWithTimestamp("📝 OCR stats initialized: total_runs=0 avg_ms=0")
}
