#!/usr/bin/env python3
"""OCR 处理 霞浦股东协议.pdf — 扫描件 → 文本"""
import subprocess, os, sys, json
from PIL import Image
import pytesseract

PDF = "/tmp/霞浦股东协议.pdf"
OUT_DIR = f"/tmp/xiapu_ocr"
os.makedirs(OUT_DIR, exist_ok=True)

def pdf_to_pages():
    """Convert PDF pages to images using pdfplumber + pixmap"""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(PDF)
    pages = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=3)  # 3x for better OCR
        pil = bitmap.to_pil()
        path = f"{OUT_DIR}/page_{i+1:03d}.png"
        pil.save(path)
        pages.append(path)
        print(f"  [{i+1}/{len(pdf)}] 第{i+1}页 → {path}")
    pdf.close()
    return pages

def ocr_page(img_path, page_num, total):
    text = pytesseract.image_to_string(
        Image.open(img_path),
        lang='chi_sim+eng',
        config='--psm 6 --oem 3'
    )
    return text.strip()

# Step 1: Convert PDF to images
print("=" * 60)
print("Step 1: PDF → 图片 (49页, 3x分辨率)")
print("=" * 60)
page_images = pdf_to_pages()
print(f"✅ 共 {len(page_images)} 页")

# Step 2: OCR
print("\n" + "=" * 60)
print("Step 2: OCR 识别 (chi_sim+eng)")
print("=" * 60)
all_text = []
for i, img_path in enumerate(page_images):
    text = ocr_page(img_path, i+1, len(page_images))
    all_text.append(f"\n{'='*60}\n第 {i+1} 页\n{'='*60}\n{text}")
    sys.stdout.write(f"\r  [{i+1}/{len(page_images)}] {len(text)} chars")
    sys.stdout.flush()
print("\n✅ OCR 完成")

# Step 3: Save result
result_text = "\n".join(all_text)
out_path = f"{OUT_DIR}/霞浦股东协议_OCR结果.txt"
with open(out_path, 'w') as f:
    f.write(result_text)
print(f"\n✅ OCR 结果保存到: {out_path}")
print(f"   总字符数: {len(result_text)}")
print(f"   总页数: {len(page_images)}")

# Step 4: Show first content preview
print("\n" + "=" * 60)
print("预览 (前3000字)")
print("=" * 60)
print(result_text[:3000])