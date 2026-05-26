import os

# GitHub GraphQL API 配置
# 如何获取 Token: https://github.com/settings/tokens
# 创建 Personal Access Token，勾选 "read:user" 和 "repo" 权限即可
# 设置环境变量 GITHUB_TOKEN 或在下方直接填写

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_HERE")

# 搜索的中国城市关键词（用户主页 location 字段）
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
