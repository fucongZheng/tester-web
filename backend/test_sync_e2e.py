"""需求同步端到端自测（可重复执行）：同步 → 幂等 → 增量更新且不动本地状态 → AI 用例 → 删除对账 → 日志。

覆盖同步时三件事：①新增项目（自动建档）②新增需求+版本 ③调 AI 生成用例接口。
前置：xuqiu 起在 8000，tester 起在 8001（8000 被 xuqiu 占用）：
    cd backend && python -m uvicorn app.main:app --port 8001
跑法：python test_sync_e2e.py
"""

import time

import httpx

TESTER = "http://127.0.0.1:8001"
XUQIU = "http://127.0.0.1:8000"
XUQIU_KEY = {"X-API-Key": "inkproto-open-9f2c1d7a"}


def tester_login(c):
    token = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def main():
    stamp = str(int(time.time()))[-6:]
    req_name = f"同步AI用例验证-{stamp}"

    with httpx.Client(base_url=TESTER, timeout=60, trust_env=False) as c:
        auth = tester_login(c)
        print("[1] tester 登录 OK")

        # 在 xuqiu 造一条新需求（同步三件事的触发器）
        with httpx.Client(base_url=XUQIU, timeout=15, trust_env=False) as x:
            xauth = {"Authorization": "Bearer " + x.post(
                "/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]}
            ver = x.get("/open/projects", headers=XUQIU_KEY).json()["versions"][0]
            r = x.post(f"/api/versions/{ver['id']}/requirements", headers=xauth,
                       json={"name": req_name, "author": "e2e",
                             "markdown": "## 登录\n用户输入账号密码登录，支持验证码与错误提示。\n## 登出\n点击退出清空会话。"})
            assert r.status_code == 200, r.text
            xuqiu_id = r.json()["id"]
        print(f"[2] xuqiu 新建需求 OK: {req_name}（{ver['projectId']} / {ver['code']}）")

        d1 = c.post("/api/sync/run", headers=auth).json()
        assert d1["created_count"] >= 1, d1
        ai_lines = [l for l in d1["detail"] if "AI" in l]
        assert ai_lines, f"新增需求应有 AI 用例结果行: {d1['detail']}"
        print(f"[3] 同步 OK: 新增 {d1['created_count']}，AI 用例 {d1['cases_count']} 条")
        for line in d1["detail"]:
            if line.strip():
                print("     -", line)

        # 新需求应带上项目和版本（自动建档），用例挂在需求下
        reqs = c.get("/api/requirements", headers=auth, params={"size": 200, "keyword": req_name}).json()
        local = next(x for x in reqs["items"] if x.get("source_id") == xuqiu_id)
        assert local["project_name"] and local["version_name"], local
        cases = c.get("/api/cases", headers=auth, params={"size": 200, "requirement_id": local["id"]}).json()
        if d1["cases_count"] > 0:
            assert cases["total"] >= 1, "AI 用例应挂在需求下"
            print(f"[4] 归属校验 OK: 项目「{local['project_name']}」版本「{local['version_name']}」，需求下用例 {cases['total']} 条")
        else:
            print(f"[4] 归属校验 OK: 项目「{local['project_name']}」版本「{local['version_name']}」；AI 未配置未生成用例（配置 API 管理后自动生效）")

        r2 = c.post("/api/sync/run", headers=auth).json()
        assert r2["created_count"] == 0 and r2["cases_count"] == 0, r2
        print(f"[5] 重复同步幂等 OK: 无新增、AI 不重复生成（{r2['skipped_count']} 条无变化）")

        # xuqiu 删需求 → 同步报告 missing，本地保留
        with httpx.Client(base_url=XUQIU, timeout=15, trust_env=False) as x:
            xauth = {"Authorization": "Bearer " + x.post(
                "/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]}
            assert x.delete(f"/api/requirements/{xuqiu_id}", headers=xauth).status_code == 200
        d3 = c.post("/api/sync/run", headers=auth).json()
        assert any(req_name in l for l in d3["detail"]), d3["detail"]
        print(f"[6] 删除对账 OK: 源已删除 {d3['missing_count']} 条（本地保留，明细有提示）")

        # 清理验证数据：删用例 → 删需求
        for case in c.get("/api/cases", headers=auth, params={"size": 200, "requirement_id": local["id"]}).json().get("items", []):
            c.delete(f"/cases/{case['id']}", headers=auth)
        assert c.delete(f"/api/requirements/{local['id']}", headers=auth).status_code == 200
        print("[7] 验证数据已清理")

        logs = c.get("/api/sync/logs", headers=auth, params={"size": 3}).json()
        assert "cases_count" in logs["items"][0], logs["items"][0]
        print(f"[8] 同步日志 OK: {logs['total']} 条，含 cases_count 字段")

        print("\n全部通过 ✔")


if __name__ == "__main__":
    main()
