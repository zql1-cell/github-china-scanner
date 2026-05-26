#!/usr/bin/env python3
"""
GitHub 中国开发者扫描器 (GraphQL API 版本)
使用 GitHub GraphQL API 高效搜索中国开发者及其开源项目
"""

import requests
import json
import time
import os
import csv
from datetime import datetime
from config import (
    GITHUB_TOKEN, CHINA_LOCATIONS, LANGUAGES,
    PAGE_SIZE, OUTPUT_DIR
)

# GraphQL API 端点
GRAPHQL_URL = "https://api.github.com/graphql"

# 请求头
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}


def graphql_query(query, variables=None):
    """执行 GraphQL 查询"""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("  ⚠️ API 速率限制，等待 60 秒...")
            time.sleep(60)
            return graphql_query(query, variables)
        else:
            print(f"  ❌ 请求失败: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        return None


# ============ 查询模板 ============

SEARCH_USERS_QUERY = """
query SearchUsers($query: String!, $cursor: String) {
  search(query: $query, type: USER, first: %d, after: $cursor) {
    userCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        ... on User {
          id
          login
          name
          bio
          location
          company
          email
          twitterUsername
          createdAt
          followers { totalCount }
          following { totalCount }
          repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}) {
            totalCount
            nodes {
              name
              description
              url
              stargazerCount
              forkCount
              primaryLanguage { name }
              createdAt
              updatedAt
              isFork
            }
          }
        }
      }
    }
  }
}
""" % PAGE_SIZE


SEARCH_REPOS_QUERY = """
query SearchRepos($query: String!, $cursor: String) {
  search(query: $query, type: REPOSITORY, first: %d, after: $cursor) {
    repositoryCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        ... on Repository {
          id
          nameWithOwner
          description
          url
          stargazerCount
          forkCount
          createdAt
          updatedAt
          pushedAt
          primaryLanguage { name }
          licenseInfo { name }
          owner {
            ... on User {
              login
              name
              location
            }
          }
          repositoryTopics(first: 10) {
            nodes {
              topic { name }
            }
          }
        }
      }
    }
  }
}
""" % PAGE_SIZE


# ============ 扫描函数 ============

def search_chinese_users(max_pages=10):
    """搜索中国开发者"""
    all_users = []
    seen_ids = set()

    for location in CHINA_LOCATIONS:
        print(f"\n🔍 搜索 location: {location} ...")
        cursor = None
        page = 0

        while page < max_pages:
            query_str = f"location:{location} type:user"
            variables = {"query": query_str, "cursor": cursor}

            result = graphql_query(SEARCH_USERS_QUERY, variables)
            if not result or "data" not in result:
                break

            search_data = result["data"]["search"]
            edges = search_data.get("edges", [])
            total = search_data.get("userCount", 0)
            has_next = search_data["pageInfo"]["hasNextPage"]
            cursor = search_data["pageInfo"]["endCursor"]

            if page == 0:
                print(f"  找到 {total} 个用户")

            for edge in edges:
                user = edge["node"]
                uid = user["id"]
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    all_users.append(user)

            page += 1
            print(f"  第 {page} 页: +{len(edges)} 用户 (累计 {len(all_users)})")

            if not has_next:
                break
            time.sleep(2)  # 避免速率限制

    return all_users


def search_china_repos(min_stars=10, max_pages=10, language=None):
    """搜索中国开发者的仓库"""
    all_repos = []
    seen_ids = set()

    for location in CHINA_LOCATIONS[:10]:  # 取前10个关键词
        lang_filter = f" language:{language}" if language else ""
        query_str = f"location:{location}{lang_filter} stars:>{min_stars} fork:false"
        print(f"\n📦 搜索仓库: {query_str} ...")
        cursor = None
        page = 0

        while page < max_pages:
            variables = {"query": query_str, "cursor": cursor}
            result = graphql_query(SEARCH_REPOS_QUERY, variables)
            if not result or "data" not in result:
                break

            search_data = result["data"]["search"]
            edges = search_data.get("edges", [])
            has_next = search_data["pageInfo"]["hasNextPage"]
            cursor = search_data["pageInfo"]["endCursor"]

            for edge in edges:
                repo = edge["node"]
                rid = repo["id"]
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    all_repos.append(repo)

            page += 1
            print(f"  第 {page} 页: +{len(edges)} 仓库 (累计 {len(all_repos)})")

            if not has_next:
                break
            time.sleep(2)

    return all_repos


# ============ 数据保存 ============

def save_users(users, filename="chinese_users.json"):
    """保存用户数据为 JSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    clean_users = []
    for u in users:
        repos = u.get("repositories", {}).get("nodes", [])
        clean_users.append({
            "login": u["login"],
            "name": u.get("name"),
            "bio": u.get("bio"),
            "location": u.get("location"),
            "company": u.get("company"),
            "email": u.get("email"),
            "followers": u.get("followers", {}).get("totalCount", 0),
            "following": u.get("following", {}).get("totalCount", 0),
            "public_repos": u.get("repositories", {}).get("totalCount", 0),
            "created_at": u.get("createdAt"),
            "top_repos": [
                {
                    "name": r["name"],
                    "stars": r["stargazerCount"],
                    "forks": r["forkCount"],
                    "language": r.get("primaryLanguage", {}).get("name"),
                    "description": r.get("description"),
                    "url": r["url"],
                }
                for r in repos
            ],
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean_users, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 用户数据已保存: {filepath}")
    print(f"   共 {len(clean_users)} 个用户")
    return filepath


def save_repos(repos, filename="chinese_repos.json"):
    """保存仓库数据为 JSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    clean_repos = []
    for r in repos:
        topics = [t["topic"]["name"] for t in r.get("repositoryTopics", {}).get("nodes", [])]
        clean_repos.append({
            "name_with_owner": r["nameWithOwner"],
            "description": r.get("description"),
            "url": r["url"],
            "stars": r["stargazerCount"],
            "forks": r["forkCount"],
            "language": r.get("primaryLanguage", {}).get("name"),
            "license": r.get("licenseInfo", {}).get("name"),
            "topics": topics,
            "owner_login": r.get("owner", {}).get("login"),
            "owner_name": r.get("owner", {}).get("name"),
            "owner_location": r.get("owner", {}).get("location"),
            "created_at": r.get("createdAt"),
            "updated_at": r.get("updatedAt"),
            "pushed_at": r.get("pushedAt"),
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean_repos, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 仓库数据已保存: {filepath}")
    print(f"   共 {len(clean_repos)} 个仓库")
    return filepath


def json_to_excel(json_file, excel_file=None):
    """JSON 转 Excel"""
    import pandas as pd

    if not excel_file:
        excel_file = json_file.replace(".json", ".xlsx")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 展平嵌套字段
    flat_data = []
    for item in data:
        row = {k: v for k, v in item.items() if not isinstance(v, (list, dict))}
        # top_repos 展开
        repos = item.get("top_repos", item.get("topics", []))
        if isinstance(repos, list) and repos:
            row["top_repo_1"] = repos[0].get("name", "") if isinstance(repos[0], dict) else repos[0]
            row["top_repo_1_stars"] = repos[0].get("stars", "") if isinstance(repos[0], dict) else ""
        flat_data.append(row)

    df = pd.DataFrame(flat_data)
    df.to_excel(excel_file, index=False)
    print(f"✅ Excel 已保存: {excel_file}")
    return excel_file


# ============ 主程序 ============

def main():
    print("=" * 60)
    print("  🇨🇳 GitHub 中国开发者扫描器 (GraphQL API)")
    print("=" * 60)
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Token: {'已配置 ✅' if GITHUB_TOKEN != 'your_github_token_here' else '❌ 未配置'}")
    print()

    if GITHUB_TOKEN == "your_github_token_here":
        print("⚠️  请先在 config.py 中配置 GITHUB_TOKEN!")
        print("   获取方式: https://github.com/settings/tokens")
        print("   勾选权限: read:user, repo")
        return

    # 选择模式
    print("请选择扫描模式:")
    print("  1. 扫描中国开发者 (按 location 搜索)")
    print("  2. 扫描中国开发者仓库 (按 stars 排序)")
    print("  3. 按语言扫描仓库 (如 Python/Go/Rust)")
    print("  4. 全部执行")
    choice = input("\n请输入 (1/2/3/4): ").strip()

    start_time = time.time()

    if choice in ("1", "4"):
        print("\n" + "=" * 40)
        print("  📋 模式1: 扫描中国开发者")
        print("=" * 40)
        users = search_chinese_users(max_pages=5)
        save_users(users)

    if choice in ("2", "4"):
        print("\n" + "=" * 40)
        print("  📦 模式2: 扫描热门仓库")
        print("=" * 40)
        repos = search_china_repos(min_stars=50, max_pages=5)
        save_repos(repos)

    if choice == "3":
        lang = input("请输入编程语言 (如 Python): ").strip()
        print(f"\n🔍 扫描 {lang} 仓库...")
        repos = search_china_repos(min_stars=10, max_pages=10, language=lang)
        save_repos(repos, filename=f"china_{lang.lower()}_repos.json")

    elapsed = time.time() - start_time
    print(f"\n⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print("完成！")


if __name__ == "__main__":
    main()
