# Source Priority

ProjectPilot V2 使用显式来源角色管理上下文：

一级来源：
1. anchor document：用户上传的主材料文件，是项目理解和生成的主依据。

二级来源：
2. supporting documents：用户上传的补充材料，可用于补充技术细节、实验结果、PPT 表述、README 风格、使用说明和测试说明。

冲突处理：

- anchor 与 supporting 冲突时，默认以 anchor 为准。
- supporting 中的内容如果 anchor 没有支撑，应使用保守表述。
- 如果 anchor 信息不足，可以引用 supporting 补充，但需要在 notes 或 meta 中保留来源映射。
- 不得把 supporting 的旧版本名称、旧指标或旧功能当作 anchor 的最终事实直接写入。
