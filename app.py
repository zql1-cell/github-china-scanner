#!/usr/bin/env python3
"""
GitHub 代码搜索器 - Web 界面
"""

import streamlit as st
import requests
import json
import os
import csv
import base64
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

# 自定义样式 - 适配深色/浅色主题
st.markdown("""
<style>
    /* 统计卡片 - 使用 CSS 变量适配主题 */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color, #f0f2f6);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid var(--border-color, #e1e4e8);
    }
    [data-testid="stMetric"] label {
        color: var(--text-color, #262730) !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text-color, #262730) !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: var(--text-color, #262730) !important;
    }

    /* 仓库卡片 */
    .repo-card {
        background-color: var(--secondary-background-color, #ffffff);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid var(--border-color, #e1e4e8);
        margin-bottom: 15px;
        color: var(--text-color, #262730);
    }
    .repo-name {
        font-size: 18px;
        font-weight: bold;
        color: var(--link-color, #0366d6);
    }
    .repo-desc {
        color: var(--text-color-secondary, #586069);
        margin: 10px 0;
    }
    .repo-stats {
        color: var(--text-color-secondary, #6a737d);
        font-size: 14px;
    }
    .tag {
        background-color: var(--secondary-background-color, #f1f8ff);
        color: var(--link-color, #0366d6);
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


def search_code_content_rest(keyword, language=None, max_results=30):
    """使用 REST API 搜索代码内容"""
    query_parts = [keyword]
    if language:
        query_parts.append(f"language:{language}")

    query_str = " ".join(query_parts)
    url = "https://api.github.com/search/code"
    params = {
        "q": query_str,
        "per_page": min(max_results, 100),
    }

    all_results = []
    page = 1
    total_count = 0

    while len(all_results) < max_results and page <= 5:
        params["page"] = page
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()

            if "items" not in data:
                st.error(f"代码搜索 API 错误: {data.get('message', '未知错误')}")
                break

            items = data["items"]
            total_count = data.get("total_count", 0)

            for item in items:
                all_results.append({
                    "文件": item.get("name", ""),
                    "路径": item.get("path", ""),
                    "仓库": item.get("repository", {}).get("full_name", ""),
                    "语言": item.get("language", ""),
                    "URL": item.get("html_url", ""),
                    "大小": item.get("size", 0),
                    "仓库描述": item.get("repository", {}).get("description", ""),
                    "仓库星标": item.get("repository", {}).get("stargazers_count", 0),
                })

            if len(items) < 30 or len(all_results) >= max_results:
                break

            page += 1
            import time
            time.sleep(1)

        except Exception as e:
            st.error(f"代码搜索请求失败: {e}")
            break

    return all_results[:max_results], total_count


def get_file_content(repo, file_path):
    """获取文件内容"""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            return content
    except Exception:
        pass
    return None


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

    # 检查 Token
    if not GITHUB_TOKEN:
        st.error("⚠️ 未检测到 GitHub Token！请在项目目录下创建 `.env` 文件并写入：\n\n```\nGITHUB_TOKEN=你的token\n```")
        st.stop()

    # 侧边栏 - 搜索条件
    with st.sidebar:
        st.header("🎯 搜索条件")

        search_type = st.radio(
            "搜索类型",
            ["📦 搜索仓库", "📝 搜索代码内容"],
            help="选择搜索类型"
        )

        keyword = st.text_input(
            "搜索关键词",
            placeholder="如: 机器学习、爬虫、def train",
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
            max_value=200,
            value=30,
            step=10,
            help="最多返回多少个结果"
        )

        search_button = st.button("🔍 开始搜索", type="primary", use_container_width=True)

    # ==================== 搜索仓库 ====================
    if search_type == "📦 搜索仓库" and search_button and keyword:
        st.markdown(f"### 🔍 搜索仓库: `{keyword}`")

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

    # ==================== 搜索代码内容 ====================
    elif search_type == "📝 搜索代码内容" and search_button and keyword:
        st.markdown(f"### 📝 搜索代码内容: `{keyword}`")

        with st.spinner("正在搜索代码..."):
            results, total_count = search_code_content_rest(keyword, language if language else None, max_results=max_results)

        if results:
            # 统计信息
            st.info(f"🔍 共找到 **{total_count:,}** 个匹配文件，显示前 **{len(results)}** 个")
            st.markdown("---")

            # 语言统计
            lang_counts = {}
            for r in results:
                lang = r["语言"] or "未知"
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            if lang_counts:
                st.markdown("#### 💻 语言分布")
                for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
                    st.markdown(f"- **{lang}**: {count} 个文件")
                st.markdown("---")

            # 显示每个匹配的代码文件
            for i, r in enumerate(results):
                with st.expander(
                    f"📄 {r['仓库']}/{r['路径']}",
                    expanded=(i < 3)
                ):
                    st.markdown(f"**📦 仓库:** {r['仓库']}")
                    if r.get("仓库描述"):
                        st.markdown(f"**📝 仓库描述:** {r['仓库描述']}")
                    st.markdown(f"**📁 文件:** `{r['路径']}`")
                    st.markdown(f"**💻 语言:** {r['语言'] or '未知'}")
                    st.markdown(f"**⭐ 仓库星标:** {r.get('仓库星标', 0):,}")
                    st.markdown(f"**🔗 [在 GitHub 中查看]({r['URL']})**")

                    st.markdown("---")

                    # 获取文件内容并高亮匹配
                    content = get_file_content(r['仓库'], r['路径'])
                    if content:
                        lines = content.split('\n')
                        matches = []
                        for j, line in enumerate(lines):
                            if keyword.lower() in line.lower():
                                start = max(0, j - 2)
                                end = min(len(lines), j + 3)
                                context_lines = lines[start:end]
                                matches.append({
                                    "line_num": j + 1,
                                    "line": line,
                                    "context": "\n".join(context_lines),
                                    "context_start": start + 1
                                })

                        if matches:
                            st.markdown(f"**🎯 找到 {len(matches)} 处匹配:**")
                            for m in matches[:8]:
                                code_lines = m["context"].split("\n")
                                numbered = []
                                for k, cl in enumerate(code_lines):
                                    ln = m["context_start"] + k
                                    marker = ">>>" if ln == m["line_num"] else "   "
                                    numbered.append(f"{marker} {ln:4d} | {cl}")
                                st.code("\n".join(numbered), language=r.get("语言", None).lower() if r.get("语言") else None)

                            if len(matches) > 8:
                                st.caption(f"... 还有 {len(matches) - 8} 处匹配，请查看原始文件")
                        else:
                            st.warning("文件已找到但无法提取具体匹配行，请直接查看原始文件")
                    else:
                        st.warning("⚠️ 无法获取文件内容（可能文件过大）")
                        st.markdown(f"[点击查看原始文件]({r['URL']})")

        else:
            st.warning("未找到匹配的代码文件，请尝试其他关键词")

    elif search_button:
        st.warning("请输入搜索关键词")

    # 使用说明
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 功能介绍

        🔍 **搜索仓库** - 搜索 GitHub 上的开源仓库，查看项目信息

        💻 **搜索代码内容** - 直接搜索代码中的关键词，如函数名、类名、配置等

        ### 搜索技巧

        **搜索仓库：**
        - 关键词越具体，搜索结果越精准
        - 设置星标数可以过滤掉低质量仓库

        **搜索代码内容：**
        - 可以搜索函数名：`def train`、`class Model`
        - 可以搜索配置：`API_KEY`、`password`
        - 可以搜索导入：`import torch`、`from transformers`
        - 结合编程语言筛选更精准

        ### 使用注意
        - 代码搜索结果会自动获取文件内容并高亮匹配行
        - 每个结果卡片可展开查看完整代码上下文
        - 建议设置合理的最大结果数，避免 API 限流
        """)


if __name__ == "__main__":
    main()
