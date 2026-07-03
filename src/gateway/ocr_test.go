package gateway

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHandleOCR_Basic(t *testing.T) {
	gw := &OpcGateway{}

	// Create a simple test image (1x1 red pixel PNG)
	img := createTestPNG(t)
	imgB64 := base64.StdEncoding.EncodeToString(img)

	body := bytes.NewBufferString(`{"image": "` + imgB64 + `"}`)
	req := httptest.NewRequest("POST", "/api/v1/ocr", body)
	w := httptest.NewRecorder()

	gw.handleOCR(w, req)

	resp := w.Result()
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	// Response should have success true
	var r Response
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		t.Errorf("failed to decode response: %v", err)
	}

	if !r.Success {
		t.Errorf("expected success=true, got false: %s", r.Error)
	}
}

func TestHandleOCR_MissingImage(t *testing.T) {
	gw := &OpcGateway{}

	body := bytes.NewBufferString(`{}`)
	req := httptest.NewRequest("POST", "/api/v1/ocr", body)
	w := httptest.NewRecorder()

	gw.handleOCR(w, req)

	resp := w.Result()
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var r Response
	json.NewDecoder(resp.Body).Decode(&r)

	if r.Success {
		t.Error("expected success=false for missing image")
	}
}

func TestHandleOCR_WrongMethod(t *testing.T) {
	gw := &OpcGateway{}

	req := httptest.NewRequest("GET", "/api/v1/ocr", nil)
	w := httptest.NewRecorder()

	gw.handleOCR(w, req)

	resp := w.Result()
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var r Response
	json.NewDecoder(resp.Body).Decode(&r)

	if r.Error == "" || r.Error != "Only POST allowed" {
		t.Errorf("expected error='Only POST allowed', got: %s", r.Error)
	}
}

func TestHandleOCRStats(t *testing.T) {
	gw := &OpcGateway{}

	req := httptest.NewRequest("GET", "/api/v1/ocr/stats", nil)
	w := httptest.NewRecorder()

	gw.handleOCRStats(w, req)

	resp := w.Result()
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var r Response
	json.NewDecoder(resp.Body).Decode(&r)

	if !r.Success {
		t.Error("expected success=true for stats")
	}
}

func TestHandleOCRStats_WrongMethod(t *testing.T) {
	gw := &OpcGateway{}

	req := httptest.NewRequest("POST", "/api/v1/ocr/stats", nil)
	w := httptest.NewRecorder()

	gw.handleOCRStats(w, req)

	resp := w.Result()
	defer resp.Body.Close()

	var r Response
	json.NewDecoder(resp.Body).Decode(&r)

	if r.Error == "" || r.Error != "Only GET allowed" {
		t.Errorf("expected error='Only GET allowed', got: %s", r.Error)
	}
}

// createTestPNG creates a minimal valid PNG (1x1 red pixel)
func createTestPNG(t *testing.T) []byte {
	// Minimal PNG: IHDR + IDAT + IEND for 1x1 red pixel
	pngData := []byte{
		0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
		// IHDR
		0x00, 0x00, 0x00, 0x0C, 0x49, 0x48, 0x44, 0x52,
		0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
		0xDE,
		// IDAT
		0x00, 0x00, 0x00, 0x07, 0x49, 0x44, 0x41, 0x54,
		0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00, 0x00,
		0x00, 0x02, 0x00, 0x01,
		// IEND
		0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
		0xAE, 0x42, 0x60, 0x82,
	}
	return pngData
}
