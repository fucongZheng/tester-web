"""AI 生成用例的提示词资产与拼装。

两份 skill 来自 D:\\ai养老（用户调优过的资产，原样放 app/prompts/，直接改文件即生效）：
- 生成用例.md     testcaseMaker  → mode="detail"  字段级细节用例（等价类/边界/幂等/权限）
- 生成闭环用例.md e2eLoopMaker   → mode="loop"    主链路闭环用例（端到端故事/子闭环/断点/口径）

两份 skill 原文是交互式 agent 流程（Step1 等确认、产 Excel/导图三件套），
这里做一次性 API 调用适配：跳过等待、不产文件、最终只输出 JSON 数组，
字段对齐 TestCase 模型（title/precondition/steps/expected/case_type/priority/remark）。
"""
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

MODES = {
    "detail": "生成用例.md",
    "loop": "生成闭环用例.md",
}

MODE_LABELS = {
    "detail": "细节用例（生成用例）",
    "loop": "闭环用例（生成闭环用例）",
}

# 交互式 skill → 一次性调用 + 结构化输出的适配指令
ONE_SHOT_ADAPTER = """你现在是「测试用例生成引擎」，下面附着一份完整的测试技能说明（Skill）。
本次是一次性 API 调用，不是交互对话，请严格遵守以下执行规则，规则与 Skill 冲突时以本规则为准：

1. 无需等待用户确认：Skill 中所有"等待确认 / 输入继续"的环节一律跳过，直接从头执行到交付。
2. 不产交付文件：不要生成 Excel / 思维导图 / Markdown 文件，不要写文件名，不要寒暄、不要复述流程、不要解释你的分析过程。
3. 分析过程（Step1~Step3 的拆解、预估算、场景表等）全部在你的思考中完成，不要输出。
4. 最终回复只能是测试用例的 JSON 数组（允许外面套一层 ```json 代码块，此外不得有任何多余文字），格式：
   [
     {
       "title": "用例标题（细节用例按 Skill 的标题规范；闭环用例保留【正向闭环】等前缀）",
       "precondition": "前置条件，分点用 \\n 换行",
       "steps": "测试步骤，编号分点用 \\n 换行",
       "expected": "预期结果，编号分点用 \\n 换行，以\"操作成功，\"或\"操作失败，\"开头",
       "priority": "P0 | P1 | P2",
       "case_type": "功能 | 接口 | UI | 性能 | 回归",
       "remark": "补充信息：细节用例填测试维度（如 FLOW/ERR/AUTH/ROBUST）；闭环用例填用例编号（如 E2E-A01）与所属模块（如 主链路-入住到退住）"
     }
   ]
5. 优先级只允许 P0/P1/P2；case_type 只能从 功能/接口/UI/性能/回归 五个里选。
6. Skill 中的列数/表格/分割行等排版要求不适用于本次输出，全部折叠进上面 7 个字段。
"""


def _load(filename: str) -> str:
    path = PROMPT_DIR / filename
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"提示词文件为空：{path}")
    return text


def system_prompt(mode: str) -> str:
    """mode → 完整 system 提示词（适配指令 + skill 原文）。"""
    if mode not in MODES:
        raise ValueError(f"未知的生成模式：{mode}（可选 {list(MODES)}）")
    return ONE_SHOT_ADAPTER + "\n---\n以下是 Skill 原文，请按其方法论设计用例：\n\n" + _load(MODES[mode])


def build_user_prompt(requirement: str, context_lines: list[str] | None = None,
                      extra: str = "") -> str:
    """组装 user 消息：上下文 + 需求内容 + 用户附加要求（可选）。"""
    parts = []
    if context_lines:
        parts.append("上下文：\n" + "\n".join(context_lines))
    parts.append(f"需求内容：\n{requirement}\n")
    if extra.strip():
        parts.append(f"附加要求（用户补充，优先级高于上文）：\n{extra.strip()}")
    return "\n\n".join(parts)
