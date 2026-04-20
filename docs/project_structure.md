# ProjectPilot 项目结构说明

本文档说明当前仓库按成熟 GitHub 项目的方式整理后的目录职责。

## 顶层结构

```text
ProjectPilot/
  app/                 # 核心应用代码
  prompts/             # LLM 任务提示词
  skills/              # Harness 上下文规则
  tests/               # 自动化测试
  docs/                # 设计、使用、演示和维护文档
  data/                # 运行时数据入口和中间产物
  outputs/             # 生成结果
  main.py              # CLI 入口
  README.md            # 项目说明
  requirements.txt     # Python 依赖
  pytest.ini           # pytest 配置
  .env.example         # 环境变量示例
  .gitignore           # Git 忽略规则
  .editorconfig        # 编辑器基础格式规则
```

## 应该提交的内容

- `app/`
- `prompts/`
- `skills/`
- `tests/`
- `docs/`
- `README.md`
- `requirements.txt`
- `main.py`
- `pytest.ini`
- `.env.example`
- `.gitignore`
- `.editorconfig`
- `.streamlit/config.toml`
- `data/raw/.gitkeep`
- `data/processed/.gitkeep`
- `data/sessions/.gitkeep`
- `outputs/.gitkeep`

## 不应该提交的内容

以下内容属于运行时产物、缓存、用户上传材料或本地环境信息：

- `__pycache__/`
- `.pytest_cache/`
- `pytest-cache-files-*/`
- `.streamlit-*.out`
- `.streamlit-*.err`
- `.env`
- `data/raw/*`
- `data/processed/*`
- `data/sessions/*`
- `outputs/*`

这些路径已写入 `.gitignore`。保留 `.gitkeep` 是为了让空目录结构能在 GitHub 中展示。

## 数据目录说明

`data/raw/` 用于 CLI 模式下放置项目材料。

`data/processed/` 用于 CLI 模式下保存：

- `documents.json`
- `profile.json`
- `verify_report.json`
- `input_manifest.json`

`data/sessions/{session_id}/` 用于 UI 模式。每次上传会创建一个独立会话：

```text
data/sessions/{session_id}/
  raw/
  processed/
  outputs/
  session.json
```

这样不同项目不会互相污染。

## 输出目录说明

`outputs/` 是 CLI 模式默认输出目录，通常包含：

- `intro.md`
- `innovation.md`
- `defense.md`
- `readme.md`
- `{task}_meta.json`
- `{task}_evidence.json`

这些是运行结果，不建议提交到 GitHub。需要展示时，可以在 README 或 Demo 中说明如何重新生成。

## Streamlit 说明

`.streamlit/config.toml` 只保留通用本地配置：

- 禁用统计采集提示
- 默认 headless 运行

Streamlit 运行日志和 smoke-test 重定向输出不应提交。

## docs 目录说明

`docs/` 当前包含：

- `README.md`：文档目录索引。
- `overview.md`：项目定位、能力和边界。
- `usage_guide.md`：CLI、UI、环境变量和输出路径。
- `architecture.md`：系统架构和模块职责。
- `harness_design.md`：Harness Engineering 三类设计。
- `data_contracts.md`：主要 JSON 产物字段说明。
- `quality_and_testing.md`：文本清洗、展示摘要、校验器和测试覆盖。
- `demo_guide.md`：3 分钟录屏演示路线。
- `roadmap.md`：后续优化方向。
- `development_record.md`：开发过程记录。
