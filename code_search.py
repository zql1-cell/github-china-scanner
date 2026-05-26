#!/usr/bin/env python3
"""
GitHub 代码内容搜索器
搜索仓库中的代码内容，如函数、类、配置等
"""

import requests
import json
import os
from datetime import datetime
from config import GITHUB_TOKEN, OUTPUT_DIR

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}


def search_code_content(keyword, language=None, repo=None, max_results=30):
    """
    搜索 GitHub 代码内容
    keyword: 搜索关键词（如函数名、类名、配置项）
    language: 编程语言筛选
    repo: 指定仓库（格式: owner/repo）
    """
    # 构建查询语句
    query_parts = [keyword]
    if language:
        query_parts.append(f"language:{language}")
    if repo:
        query_parts.append(f"repo:{repo}")

    query_str = " ".join(query_parts)

    # GitHub GraphQL API 不支持代码搜索
    # 使用 REST API: GET /search/code
    url = "https://api.github.com/search/code"
    params = {
        "q": query_str,
        "per_page": min(max_results, 100),
    }

    all_results = []
    page = 1

    while len(all_results) < max_results and page <= 10:
        params["page"] = page
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()

            if "items" not in data:
                print(f"API 错误: {data.get('message', '未知错误')}")
                break

            items = data["items"]
            total_count = data.get("total_count", 0)

            if not all_results:
                print(f"🔍 找到 {total_count} 个匹配的代码文件")

            for item in items:
                all_results.append({
                    "文件": item.get("name", ""),
                    "路径": item.get("path", ""),
                    "仓库": item.get("repository", {}).get("full_name", ""),
                    "语言": item.get("language", ""),
                    "URL": item.get("html_url", ""),
                    "大小": item.get("size", 0),
                })

            if len(items) < 30 or len(all_results) >= max_results:
                break

            page += 1
            import time
            time.sleep(1)

        except Exception as e:
            print(f"请求失败: {e}")
            break

    return all_results[:max_results]


def get_file_content(repo, file_path):
    """获取文件内容"""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            import base64
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            return content
    except Exception as e:
        print(f"获取文件内容失败: {e}")
    return None


def search_with_content(keyword, language=None, max_results=20):
    """搜索代码并获取内容"""
    results = search_code_content(keyword, language, max_results=max_results)

    print(f"\n📋 获取文件内容...")
    for i, r in enumerate(results[:10]):  # 只获取前10个文件的内容
        content = get_file_content(r["仓库"], r["路径"])
        if content:
            # 在内容中搜索关键词的上下文
            lines = content.split("\n")
            matches = []
            for j, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    # 获取上下文（前后各3行）
                    start = max(0, j - 3)
                    end = min(len(lines), j + 4)
                    context = "\n".join(lines[start:end])
                    matches.append({
                        "行号": j + 1,
                        "上下文": context
                    })
            r["匹配内容"] = matches
            print(f"  ✅ {r['仓库']}/{r['路径']} ({len(matches)} 处匹配)")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python code_search.py \"关键词\" [--lang Python] [--repo owner/repo]")
        sys.exit(1)

    keyword = sys.argv[1]
    language = None
    repo = None

    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            language = sys.argv[idx + 1]

    if "--repo" in sys.argv:
        idx = sys.argv.index("--repo")
        if idx + 1 < len(sys.argv):
            repo = sys.argv[idx + 1]

    print(f"\n🔍 搜索代码内容: {keyword}")
    if language:
        print(f"   语言: {language}")
    if repo:
        print(f"   仓库: {repo}")

    results = search_code_content(keyword, language, repo)

    print(f"\n{'='*80}")
    print(f"  📊 搜索结果 (共 {len(results)} 个文件)")
    print(f"{'='*80}\n")

    for i, r in enumerate(results, 1):
        print(f"  [{i}] 📄 {r['文件']}")
        print(f"       📁 {r['路径']}")
        print(f"       📦 {r['仓库']}")
        print(f"       💻 {r['语言'] or '未知'}")
        print(f"       🔗 {r['URL']}")
        print()
