#!/usr/bin/env python3
"""
浏览器自动化脚本 - 封装常用操作
通过 CDP 连接 Chrome 进行网页操作
"""
import asyncio
import sys
import json
from typing import Optional, List, Dict
from playwright.async_api import async_playwright

CDP_URL = "http://localhost:9222"

async def search_google(query: str, max_results: int = 5) -> List[Dict]:
    """在 Google 搜索并返回结果"""
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto('https://www.google.com')
        await page.fill('textarea[name=q]', query)
        await page.press('textarea[name=q]', 'Enter')
        await asyncio.sleep(2)
        
        # 获取搜索结果
        headings = await page.locator('h3').all_text_contents()
        links = await page.locator('a h3').locator('..').all()
        
        for i, (title, link) in enumerate(zip(headings[:max_results], links[:max_results]), 1):
            href = await link.get_attribute('href') if link else ''
            results.append({
                'index': i,
                'title': title,
                'url': href
            })
        
        await browser.close()
    return results


async def get_page_text(url: str, selector: str = 'body') -> str:
    """获取网页文本内容"""
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto(url)
        await asyncio.sleep(2)
        
        text = await page.locator(selector).text_content()
        await browser.close()
        return text[:5000]  # 限制长度


async def extract_table(url: str, table_index: int = 0) -> List[List[str]]:
    """提取网页表格数据"""
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto(url)
        await asyncio.sleep(2)
        
        tables = await page.locator('table').all()
        if table_index >= len(tables):
            await browser.close()
            return []
        
        rows = await tables[table_index].locator('tr').all()
        data = []
        for row in rows:
            cells = await row.locator('td, th').all_text_contents()
            data.append(cells)
        
        await browser.close()
        return data


async def open_url(url: str) -> str:
    """在浏览器中打开 URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto(url)
        title = await page.title()
        await browser.close()
        return f"已打开: {title}"


async def screenshot(url: Optional[str] = None, output_path: str = '/tmp/browser_screenshot.png') -> str:
    """截取网页屏幕"""
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        if url:
            await page.goto(url)
            await asyncio.sleep(2)
        
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
        return output_path


async def check_status() -> Dict:
    """检查 Chrome 连接状态"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            contexts = browser.contexts
            pages = []
            for ctx in contexts:
                for page in ctx.pages:
                    pages.append({
                        'title': await page.title(),
                        'url': page.url
                    })
            await browser.close()
            return {
                'connected': True,
                'contexts': len(contexts),
                'pages': pages
            }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }


def main():
    if len(sys.argv) < 2:
        print("用法: browser_tool.py <command> [args...]")
        print("命令:")
        print("  search <query> [max_results]  - Google 搜索")
        print("  text <url> [selector]         - 获取网页文本")
        print("  table <url> [table_index]     - 提取表格数据")
        print("  open <url>                    - 打开网页")
        print("  screenshot [url] [output]     - 截图")
        print("  status                        - 检查连接状态")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'search':
        query = sys.argv[2]
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = asyncio.run(search_google(query, max_results))
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif command == 'text':
        url = sys.argv[2]
        selector = sys.argv[3] if len(sys.argv) > 3 else 'body'
        text = asyncio.run(get_page_text(url, selector))
        print(text)
    
    elif command == 'table':
        url = sys.argv[2]
        table_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        data = asyncio.run(extract_table(url, table_index))
        print(json.dumps(data, ensure_ascii=False, indent=2))
    
    elif command == 'open':
        url = sys.argv[2]
        result = asyncio.run(open_url(url))
        print(result)
    
    elif command == 'screenshot':
        url = sys.argv[2] if len(sys.argv) > 2 else None
        output = sys.argv[3] if len(sys.argv) > 3 else '/tmp/browser_screenshot.png'
        path = asyncio.run(screenshot(url, output))
        print(f"截图保存到: {path}")
    
    elif command == 'status':
        status = asyncio.run(check_status())
        print(json.dumps(status, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
