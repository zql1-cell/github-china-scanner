#!/usr/bin/env python3
"""
GitHub 代码搜索器 - Web 界面
"""

import streamlit as st
import requests
import json
import os
import csv
from datetime import datetime
from config import GITHUB_TOKEN, OUTPUT_DIR

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# 页面配置
st.set_page_config(
    page_title="GitHub 代码搜索器",
    page_icon="🔍",
    layout="wide"
)

# 自定义样式
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .repo-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e1e4e8;
        margin-bottom: 15px;
    }
    .repo-name {
        font-size: 18px;
        font-weight: bold;
        color: #0366d6;
    }
    .repo-desc {
        color: #586069;
        margin: 10px 0;
    }
    .repo-stats {
        color: #6a737d;
        font-size: 14px;
    }
    .tag {
        background-color: #f1f8ff;
        color: #0366d6;
        padding: 2px 8px;
        border-radius: 15px;
        font-size: 12px;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)


def search_code(keyword, language=None, min_stars=0, max_results=50):
    """搜索 GitHub 代码和仓库"""
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
    progress_bar = st.progress(0)
    status_text = st.empty()

    while len(all_repos) < max_results:
        payload = {
            "query": graphql_query,
            "variables": {"query": query_str, "cursor": cursor}
        }
        try:
            resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
            data = resp.json()

            if "data" not in data:
                st.error(f"API 错误: {data.get('message', '未知错误')}")
                break

            search = data["data"]["search"]
            total = search["repositoryCount"]
            edges = search["edges"]
            has_next = search["pageInfo"]["hasNextPage"]
            cursor = search["pageInfo"]["endCursor"]

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

            progress = min(len(all_repos) / max_results, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"已收集 {len(all_repos)} / {min(max_results, total)} 个仓库")

            if not has_next:
                break

            import time
            time.sleep(1)

        except Exception as e:
            st.error(f"请求失败: {e}")
            break

    progress_bar.empty()
    status_text.empty()
    return all_repos[:max_results]


def save_results(repos, keyword):
    """保存结果到文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:30]

    json_file = os.path.join(OUTPUT_DIR, f"search_{safe_keyword}_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2)

    csv_file = os.path.join(OUTPUT_DIR, f"search_{safe_keyword}_{timestamp}.csv")
    if repos:
        with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=repos[0].keys())
            writer.writeheader()
            writer.writerows(repos)

    return json_file, csv_file


def main():
    st.title("🔍 GitHub 代码搜索器")
    st.markdown("搜索 GitHub 上的开源项目，只搜不下，快速发现优质代码")

    # 侧边栏 - 搜索条件
    with st.sidebar:
        st.header("🎯 搜索条件")

        keyword = st.text_input(
            "搜索关键词",
            placeholder="如: 机器学习、爬虫、API",
            help="输入你想搜索的关键词"
        )

        language = st.selectbox(
            "编程语言",
            ["", "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C", "C#", 
             "Kotlin", "Swift", "PHP", "Ruby", "Dart", "Lua", "Scala", "R", "Vue", "React"],
            help="选择编程语言筛选"
        )

        min_stars = st.number_input(
            "最低星标数",
            min_value=0,
            max_value=100000,
            value=0,
            step=10,
            help="只显示星标数大于此值的仓库"
        )

        max_results = st.slider(
            "最大结果数",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            help="最多返回多少个结果"
        )

        search_button = st.button("🔍 开始搜索", type="primary", use_container_width=True)

    # 主区域 - 搜索结果
    if search_button and keyword:
        st.markdown(f"### 🔍 搜索: `{keyword}`")
        
        with st.spinner("正在搜索..."):
            repos = search_code(keyword, language if language else None, min_stars, max_results)

        if repos:
            # 统计信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📦 仓库总数", len(repos))
            with col2:
                avg_stars = sum(r["星标"] for r in repos) // len(repos)
                st.metric("⭐ 平均星标", f"{avg_stars:,}")
            with col3:
                languages = set(r["语言"] for r in repos if r["语言"])
                st.metric("💻 编程语言", len(languages))
            with col4:
                locations = set(r["作者位置"] for r in repos if r["作者位置"])
                st.metric("📍 地区分布", len(locations))

            # 语言分布图表
            st.markdown("#### 📊 语言分布")
            lang_counts = {}
            for r in repos:
                lang = r["语言"] or "未知"
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
            if lang_counts:
                import pandas as pd
                lang_df = pd.DataFrame(list(lang_counts.items()), columns=["语言", "数量"])
                lang_df = lang_df.sort_values("数量", ascending=False)
                st.bar_chart(lang_df.set_index("语言"))

            # 结果列表
            st.markdown("#### 📋 搜索结果")
            
            for i, repo in enumerate(repos):
                with st.container():
                    # 仓库卡片
                    st.markdown(f"""
                    <div class="repo-card">
                        <div class="repo-name">📦 {repo['仓库']}</div>
                        <div class="repo-desc">{repo['描述'] or '无描述'}</div>
                        <div class="repo-stats">
                            ⭐ {repo['星标']:,} &nbsp;|&nbsp; 🍴 {repo['Fork']:,} &nbsp;|&nbsp; 
                            💻 {repo['语言'] or '未知'} &nbsp;|&nbsp; 📍 {repo['作者位置'] or '未知'} &nbsp;|&nbsp; 
                            👤 {repo['作者']}
                        </div>
                        {"<div>" + "".join(f'<span class="tag">{t}</span>' for t in repo["主题标签"].split(", ") if t) + "</div>" if repo["主题标签"] else ""}
                        <div style="margin-top: 10px;">
                            <a href="{repo['链接']}" target="_blank">🔗 在 GitHub 中查看</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # 保存按钮
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存结果到本地", use_container_width=True):
                    json_file, csv_file = save_results(repos, keyword)
                    st.success(f"已保存!\n- JSON: {json_file}\n- CSV: {csv_file}")
            with col2:
                # 导出为 CSV 下载
                import pandas as pd
                df = pd.DataFrame(repos)
                csv_data = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 下载 CSV 文件",
                    data=csv_data,
                    file_name=f"github_search_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.warning("未找到匹配的仓库，请尝试其他关键词")

    elif search_button:
        st.warning("请输入搜索关键词")

    # 使用说明
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 功能介绍
        
        🔍 **搜索关键词** - 输入你想搜索的内容，如"机器学习"、"爬虫"、"API"
        
        💻 **编程语言** - 按编程语言筛选结果
        
        ⭐ **最低星标数** - 只显示高质量的仓库
        
        📊 **语言分布** - 查看搜索结果的编程语言占比
        
        💾 **保存结果** - 导出为 JSON 或 CSV 文件
        
        ### 使用技巧
        
        1. 关键词越具体，搜索结果越精准
        2. 设置星标数可以过滤掉低质量仓库
        3. 结合多种条件可以找到最符合需求的项目
        """)


if __name__ == "__main__":
    main()
