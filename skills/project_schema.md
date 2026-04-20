# Project Schema

ProjectPilot V2 面向任意项目材料，不预设项目类型。系统需要从 anchor document 和 supporting documents 中抽取通用项目画像：

- anchor_document
- supporting_documents
- source_roles
- project_name
- project_type
- background
- pain_points
- target_users
- core_technologies
- system_architecture
- system_modules
- innovation_points
- experiment_results
- deliverables
- limitations
- future_work

抽取原则：

- anchor document 是主事实来源。
- supporting documents 只做补充细节、示例、使用说明或表达风格增强。
- 若 supporting 与 anchor 冲突，默认优先 anchor。
- 信息不足时写“证据不足”或使用保守表述，不编造。
