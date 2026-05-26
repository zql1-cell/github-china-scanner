import os
import streamlit as st

# GitHub API 配置
# 优先从 Streamlit secrets 读取，否则从环境变量读取
try:
    GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
except Exception:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# 如果环境变量也没有，尝试读取 .env 文件
if not GITHUB_TOKEN:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_TOKEN=") and not line.startswith("#"):
                    GITHUB_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

# 搜索的中国城市关键词
CHINA_LOCATIONS = [
    "China", "中国", "CN",
    "Beijing", "北京", "Shanghai", "上海",
    "Shenzhen", "深圳", "Hangzhou", "杭州",
    "Guangzhou", "广州", "Chengdu", "成都",
    "Nanjing", "南京", "Wuhan", "武汉",
    "Xi'an", "西安", "Chongqing", "重庆",
    "Suzhou", "苏州", "Dongguan", "东莞",
    "Tianjin", "天津", "Zhengzhou", "郑州",
    "Xiamen", "厦门", "Qingdao", "青岛",
    "PRC", "Hong Kong", "香港", "Taiwan", "台湾",
]

# 关注的编程语言
LANGUAGES = [
    "Python", "Java", "JavaScript", "TypeScript",
    "Go", "Rust", "C++", "C", "C#",
    "Kotlin", "Swift", "PHP", "Ruby",
    "Dart", "Lua", "Scala", "R",
    "Vue", "React", "HTML", "CSS",
]

# 每次查询数量（最大100）
PAGE_SIZE = 100

# 数据保存路径
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
