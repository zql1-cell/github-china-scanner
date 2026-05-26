# GitHub 中国开源代码搜索器 🔍

> **不下载代码**，只搜索和收集元数据（仓库名、描述、星标、作者等）
> 输出文件仅几KB，完全不占空间

## 快速开始

### 第1步：获取 GitHub Token
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `read:user` 和 `repo` 权限
4. 复制生成的 Token

### 第2步：配置 Token
编辑 `config.py`，把 Token 填进去：
```python
GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # 粘贴你的 Token
```

### 第3步：搜索
```bash
# 安装依赖（只需 requests）
pip install requests

# 搜索关键词
python search.py "机器学习"

# 按语言筛选
python search.py "爬虫" --lang Python

# 只看热门项目（100星以上）
python search.py "API框架" --lang Go --min-stars 100

# 搜索中国开发者的项目
python search.py "深度学习" --lang Python
```

### 第4步：全量扫描（可选）
```bash
# 扫描所有中国开发者
python scanner.py
# 选择模式 1/2/3/4
```

## 输出示例
搜索结果保存在 `output/` 目录：
- `search_机器学习_20260522.json` - JSON 格式
- `search_机器学习_20260522.csv` - CSV 格式（可直接用 Excel 打开）

每个结果包含：
- 仓库名、描述、星标数、Fork数
- 编程语言、许可证、主题标签
- 作者信息（用户名、位置、简介）
- 直接链接

## 搜索语法示例
```bash
# 搜索特定领域的代码
python search.py "大语言模型" --lang Python
python search.py "微信小程序" --lang JavaScript
python search.py "物联网 IoT" --lang C++
python search.py "区块链 DeFi" --min-stars 500

# 搜索中国开发者常用的框架
python search.py "gin" --lang Go --min-stars 1000
python search.py "fastapi" --lang Python --min-stars 5000
```

## 文件说明
- `config.py` - 配置文件（Token、搜索关键词等）
- `search.py` - ⭐ 轻量搜索器（推荐日常使用）
- `scanner.py` - 全量扫描器（扫描所有中国开发者）
- `requirements.txt` - 依赖包
- `output/` - 输出目录（自动创建）
