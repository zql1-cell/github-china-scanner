#!/usr/bin/env python3
"""
GitHub 代码搜索器 - 只搜索关键信息，不下载代码
用法: python search.py "关键词" [--lang Python] [--min-stars 100]
"""

import requests
import json
import os
import sys
import argparse
from datetime import datetime
from config import GITHUB_TOKEN, OUTPUT_DIR

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}


def search_code(keyword, language=None, min_stars=0, max_results=50):
    """
    搜索 GitHub 代码和仓库
    只返回元数据，不下载任何代码文件
    """
    # 构建查询语句
    query_parts = [f"{keyword} in:readme"]
    if language:
        query_parts.append(f"language:{language}")
    if min_stars > 0:
        query_parts.append(f"stars:>={min_stars}")

    query_str = " ".join(query_parts)

    graphql_query = """
    query($query: String!, $cursor: String) {
      search(query: $query, type: REPOSITORY, first: 20, after: $cursor) {
        repositoryCount
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            ... on Repository {
              nameWithOwner
              description
              url
              stargazerCount
              forkCount
              createdAt
              pushedAt
              primaryLanguage { name }
              licenseInfo { name }
              owner {
                ... on User {
                  login
                  name
                  location
                  bio
                }
              }
              repositoryTopics(first: 5) {
                nodes { topic { name } }
              }
            }
          }
        }
      }
    }
    """

    all_repos = []
    cursor = None

    while len(all_repos) < max_results:
        payload = {
            "query": graphql_query,
            "variables": {"query": query_str, "cursor": cursor}
        }
        resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
        data = resp.json()

        if "data" not in data:
            print(f"API 错误: {data.get('message', '未知错误')}")
            break

        search = data["data"]["search"]
        total = search["repositoryCount"]
        edges = search["edges"]
        has_next = search["pageInfo"]["hasNextPage"]
        cursor = search["pageInfo"]["endCursor"]

        if not all_repos:
            print(f"🔍 找到 {total} 个匹配仓库")

        for edge in edges:
            repo = edge["node"]
            topics = [t["topic"]["name"] for t in repo.get("repositoryTopics", {}).get("nodes", [])]
            all_repos.append({
                "仓库": repo["nameWithOwner"],
                "描述": repo.get("description", ""),
                "星标": repo["stargazerCount"],
                "Fork": repo["forkCount"],
                "语言": (repo.get("primaryLanguage") or {}).get("name", ""),
                "许可证": (repo.get("licenseInfo") or {}).get("name", ""),
                "作者": (repo.get("owner") or {}).get("login", ""),
                "作者位置": (repo.get("owner") or {}).get("location", ""),
                "作者简介": (repo.get("owner") or {}).get("bio", ""),
                "主题标签": ", ".join(topics),
                "更新时间": repo.get("pushedAt", ""),
                "链接": repo["url"],
            })

        print(f"  已收集 {len(all_repos)} / {min(max_results, total)}")
        if not has_next:
            break

        import time
        time.sleep(2)

    return all_repos[:max_results]


def display_results(repos):
    """在终端中美观展示结果"""
    print("\n" + "=" * 80)
    print(f"  📊 搜索结果 (共 {len(repos)} 个仓库)")
    print("=" * 80 + "\n")

    for i, repo in enumerate(repos, 1):
        print(f"  [{i}] ⭐{repo['星标']:>6}  🍴{repo['Fork']:>5}  {repo['仓库']}")
        if repo["描述"]:
            print(f"       📝 {repo['描述'][:70]}")
        print(f"       💻 {repo['语言'] or '未知'}  |  📍 {repo['作者位置'] or '未知'}  |  👤 {repo['作者']}")
        if repo["主题标签"]:
            print(f"       🏷️  {repo['主题标签']}")
        print(f"       🔗 {repo['链接']}")
        print()


def save_results(repos, keyword):
    """保存结果到文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:30]

    # JSON
    json_file = os.path.join(OUTPUT_DIR, f"search_{safe_keyword}_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2)

    # CSV
    csv_file = os.path.join(OUTPUT_DIR, f"search_{safe_keyword}_{timestamp}.csv")
    if repos:
        with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=repos[0].keys())
            writer.writeheader()
            writer.writerows(repos)

    print("\n💾 已保存:")
    print(f"   {json_file}")
    print(f"   {csv_file}")
    print(f"   文件大小: {os.path.getsize(json_file) / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="GitHub 代码搜索器 - 只搜不下")
    parser.add_argument("keyword", help="搜索关键词，如: 机器学习、爬虫、API")
    parser.add_argument("--lang", help="编程语言筛选，如: Python, Go", default=None)
    parser.add_argument("--min-stars", type=int, default=0, help="最低星标数")
    parser.add_argument("--max", type=int, default=50, help="最大结果数")
    args = parser.parse_args()

    print(f"\n🔍 搜索: {args.keyword}")
    if args.lang:
        print(f"   语言: {args.lang}")
    if args.min_stars:
        print(f"   最低星标: {args.min_stars}")

    repos = search_code(args.keyword, args.lang, args.min_stars, args.max)
    display_results(repos)
    save_results(repos, args.keyword)


if __name__ == "__main__":
    import csv
    main()
