# 系统架构

## 总体流程

```text
Upload / Raw Docs
  -> Parse
  -> Assign Roles
  -> Clean
  -> Extract Generic Profile
  -> Build Display Summaries
  -> Retrieve Evidence
  -> LLM Generate or Rule Fallback
  -> Verify
  -> Retry Repair
  -> Outputs
```

## 输入模型

ProjectPilot V2 使用两类文档角色。

| 角色 | 是否必填 | 作用 |
| --- | --- | --- |
| `anchor` | 必填，单文件 | 主事实来源，系统优先围绕它理解项目 |
| `supporting` | 可选，多文件 | 补充技术细节、PPT 表述、README 风格、测试说明等 |

当 anchor 和 supporting 存在冲突时，默认以 anchor 为准。

## 运行入口

### CLI 入口

`main.py` 提供命令行入口：

```powershell
python main.py status
python main.py doctor
python main.py extract
python main.py verify
python main.py generate --type defense
python main.py runall
```

CLI 默认使用：

- `data/raw/`
- `data/processed/`
- `outputs/`

### UI 入口

Streamlit 页面入口：

```powershell
streamlit run app/ui.py
```

UI 每次上传都会创建独立 session：

```text
data/sessions/{session_id}/
  raw/
  processed/
  outputs/
  session.json
```

这样多个项目不会共用同一份 profile、evidence 或输出。

## 核心模块职责

| 文件 | 职责 |
| --- | --- |
| `app/parser.py` | 读取 txt/md/pdf/docx/pptx/doc/ppt，输出带 role 的文档对象 |
| `app/chunker.py` | 文本分段和基础切块 |
| `app/extractor.py` | 清洗文本、抽取通用项目画像、构建展示摘要 |
| `app/retriever.py` | 按任务检索 evidence，anchor 优先，supporting 补充 |
| `app/llm_client.py` | OpenAI-compatible LLM 客户端和可用性检测 |
| `app/generator.py` | LLM/规则双模式生成 intro、innovation、defense、readme |
| `app/verifier.py` | 校验 profile、输出文本、来源覆盖和字段重复污染 |
| `app/pipeline.py` | 编排 extract、verify、generate、retry 和文件写出 |
| `app/ui.py` | Streamlit 产品页面 |
| `app/tool_registry.py` | 本地工具注册层，包含文件检索、Office 转换和知识图谱摘要能力 |

## 生成链路

生成某个任务时，pipeline 会执行：

1. 读取或重新抽取 profile。
2. 加载 documents。
3. 调用 retriever 获取 evidence。
4. evidence 检索采用轻量 lexical + semantic 混合索引。
5. 调用 generator 生成初稿。
6. 调用 verifier 校验初稿，并输出 claim-support 对齐结果。
7. 如果有关键 warning，执行一次 retry repair。
8. 写出最终 markdown、meta、evidence 和 verify report。

输出文件：

```text
outputs/{task}.md
outputs/{task}_meta.json
outputs/{task}_evidence.json
data/processed/verify_report.json
```

UI session 下对应写入：

```text
data/sessions/{session_id}/outputs/{task}.md
data/sessions/{session_id}/outputs/{task}_meta.json
data/sessions/{session_id}/outputs/{task}_evidence.json
```
