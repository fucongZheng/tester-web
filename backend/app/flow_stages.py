"""测试流程环节注册表 —— 环节定义的唯一来源。

环节顺序、名称、可跳过/可驳回等规则集中在这里；
路由（状态机）、质量快照、测试报告、前端展示都通过环节 key
（如 dev_handover）引用，不出现魔法数字。

新增/调整环节时只改这个文件：
- 在 STAGE_KEYS / STAGE_NAMES 中插入或改名，编号（STAGE_NO）按顺序自动生成；
- 存量数据的历史编号另配迁移（见 seed.py）。
- flow 路由里的通过门槛按 key 注册在 STAGE_GATES（见 routers/flow.py）。
"""

STAGE_KEYS = [
    "case_writing",   # 测试用例编写
    "case_review",    # 测试用例评审
    "dev_handover",   # 开发提测（提测通过 / 驳回提测）
    "ai_api",         # AI接口测试(代码测试)
    "ai_ui",          # AI界面测试
    "manual",         # 人工测试（展示为 人工第N轮测试）
    "regression",     # 回归测试
    "acceptance",     # 产品验收
    "launch",         # 上线+生产环境验证
]

STAGE_NAMES = {
    "case_writing": "测试用例编写",
    "case_review": "测试用例评审",
    "dev_handover": "开发提测",
    "ai_api": "AI接口测试(代码测试)",
    "ai_ui": "AI界面测试",
    "manual": "人工测试",
    "regression": "回归测试",
    "acceptance": "产品验收",
    "launch": "上线+生产环境验证",
}

STAGE_NO = {key: no for no, key in enumerate(STAGE_KEYS)}
NO_TO_KEY = {no: key for key, no in STAGE_NO.items()}
FIRST_STAGE_NO = 0
LAST_STAGE_NO = len(STAGE_KEYS) - 1

# 允许跳过的环节：两个 AI 测试环节在暂无对应资产时可跳过
SKIPPABLE_STAGES = {"ai_api", "ai_ui"}
# 允许驳回的环节：提测可驳回（流程挂起，重新提测后恢复）；产品验收驳回则回到人工测试
REJECTABLE_STAGES = {"dev_handover", "acceptance"}

# 套件类型 → 执行记录归属的流程环节 key（套件批量执行时给记录打环节标记）
SUITE_TYPE_STAGE = {"冒烟": "dev_handover", "第一轮功能": "manual", "回归": "regression"}


def stage_key(stage_no: int) -> str:
    return NO_TO_KEY.get(stage_no, "")


def stage_label(stage_no: int, round_no: int = 1) -> str:
    key = stage_key(stage_no)
    if key == "manual":
        return f"人工第{round_no or 1}轮测试"
    return STAGE_NAMES.get(key, f"环节{stage_no}")
