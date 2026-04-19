# 3分钟答辩稿

各位老师好，我汇报的工具是 ProjectPilot：项目材料理解与答辩生成助手，它服务的项目背景是《基于改进Yolo和PCBNet的景区行人重识别系统》。

这个选题解决的不是单纯的行人重识别算法问题，而是项目交付中的真实痛点：资料分散、版本表述不统一、人工整理 README 和答辩稿效率低。在准备课程作业、README 和答辩稿时，材料往往分散在 PDF、Markdown、PPT 提纲和说明文档中，人工整理容易混入旧版本信息、论文页眉页脚、目录和致谢等脏文本。

ProjectPilot 的流程是：先读取真实项目材料，清洗并分块，再抽取项目名称、核心技术、系统模块、背景、痛点和创新点等项目画像；随后按 intro、innovation、defense 等不同任务检索相关证据，最后把证据、规则和任务要求交给 LLM 生成内容。当前已识别的技术背景包括 YOLOv8、YOLO、SENet、ResNet50、PCBNet、TriHard Loss，系统能力覆盖 多文档解析、文本清洗与分块、结构化项目画像、证据检索、LLM 生成、自动校验与重试。

在 Harness Engineering 设计上，我做了三层控制。第一是上下文管理，通过 skills/project_schema、writing_rules、source_priority 和 prompts 明确字段、写作规则与来源优先级。第二是外部工具调用，系统通过本地 parser 读取 PDF 和 Markdown，通过 CLI 与 Streamlit 触发流程，并可配置 OpenAI-compatible LLM API。第三是验证与反馈闭环，verifier 会检查必填字段、脏文本、来源覆盖、别名冲突和 unsupported claims；如果生成稿存在关键 warning，pipeline 会把 warning、原稿和 evidence 送回 retry prompt 进行一次有限修复。

因此，这个工具不是网页聊天，而是 Retrieval-Grounded + Harness-Controlled 的 AI 原生工作流。它能把分散材料转成可追踪证据，再生成更干净、更可信、可直接用于 README 和答辩的内容。我的汇报完毕，谢谢各位老师。