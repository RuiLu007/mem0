#!/usr/bin/env python3
"""
seed_hotel_data_v2.py — 酒店客服场景微信聊天记录模拟数据生成器

场景覆盖:
  1. 预订咨询 (booking)
  2. 入住办理 (checkin)
  3. 设施询问 (facilities)
  4. 投诉处理 (complaint)
  5. 退房结算 (checkout)

用法:
  python scripts/seed_hotel_data_v2.py [--host http://localhost:8765] [--user wechat_test_001]
"""

import argparse
import json
import time
import requests
from datetime import datetime

# ── 模拟对话数据 ──────────────────────────────────────────────────────────────
# 格式: { scene, role(customer/staff), content }
HOTEL_CONVERSATIONS = [
    # ── 场景1: 预订咨询 ──────────────────────────────────────────────────────
    {
        "scene": "booking",
        "dialogs": [
            {"role": "customer", "content": "你好，我想预订5月3号到5月6号的房间，有空房吗？"},
            {"role": "staff", "content": "您好！5月3-6日共3晚，目前有标准大床房和商务套房可选。请问您有什么偏好？"},
            {"role": "customer", "content": "我需要高楼层的无烟大床房，最好能看到城市景观，预算不超过500元/晚"},
            {"role": "staff", "content": "完美！我们18楼的豪华大床房正好满足，398元/晚，含早餐，景观绝佳。要帮您预留吗？"},
            {"role": "customer", "content": "好的，帮我预订18楼的豪华大床房，姓名张伟，手机13812345678"},
            {"role": "staff", "content": "已为张先生预订18楼1806房，订单号BK20260503001，入住当天请持身份证前台办理，押金1000元。"},
        ]
    },
    # ── 场景2: 入住办理 ──────────────────────────────────────────────────────
    {
        "scene": "checkin",
        "dialogs": [
            {"role": "customer", "content": "我是张伟，今天下午3点到，可以提前入住吗？订单号BK20260503001"},
            {"role": "staff", "content": "张先生您好！您的预订已确认，下午2点起即可办理入住，1806房已准备好。"},
            {"role": "customer", "content": "太好了，另外我需要加一张行军床，我太太和我一起入住"},
            {"role": "staff", "content": "明白，已为您安排加床，每晚额外50元。房间备注：双人入住，加床服务。"},
            {"role": "customer", "content": "押金可以刷微信支付吗？"},
            {"role": "staff", "content": "可以，押金1000元支持微信/支付宝/银行卡，退房时会原路返还。入住愉快！"},
        ]
    },
    # ── 场景3: 设施询问 ──────────────────────────────────────────────────────
    {
        "scene": "facilities",
        "dialogs": [
            {"role": "customer", "content": "请问酒店有游泳池吗？开放时间是几点到几点？"},
            {"role": "staff", "content": "有的！室内恒温游泳池在B1层，开放时间07:00-22:00，住客免费使用。"},
            {"role": "customer", "content": "健身房呢？器械是否齐全"},
            {"role": "staff", "content": "健身房在2楼，24小时开放，跑步机、哑铃、综合力量器械一应俱全，私教课需提前预约。"},
            {"role": "customer", "content": "早餐是自助餐吗？在哪里用餐？几点到几点"},
            {"role": "staff", "content": "是的，自助早餐在1楼逸厨餐厅，07:00-09:30，含中西式餐品50余种。您的房费已含早餐。"},
            {"role": "customer", "content": "停车场收费吗，我明天自驾过来"},
            {"role": "staff", "content": "地下停车场B2-B3，住客每天30元，进出凭房卡刷卡，共200个车位，建议提前电话确认。"},
        ]
    },
    # ── 场景4: 投诉处理 ──────────────────────────────────────────────────────
    {
        "scene": "complaint",
        "dialogs": [
            {"role": "customer", "content": "我要投诉！昨晚1802房噪音很大，整夜空调嗡嗡响，完全没睡着"},
            {"role": "staff", "content": "非常抱歉给您带来不好的入住体验！立即安排工程师上门检查维修。请问您现在方便吗？"},
            {"role": "customer", "content": "我现在已经退房了，这严重影响了我的休息，希望赔偿"},
            {"role": "staff", "content": "完全理解您的心情，这是我们的失误。为补偿您，赠送500元代金券，下次入住免费升级套房，并减免昨晚房费200元。"},
            {"role": "customer", "content": "好吧，可以接受，代金券怎么领取"},
            {"role": "staff", "content": "已发送到您的微信，有效期一年。投诉工单号CP20260504001已记录，品质部将跟进整改。感谢您的反馈！"},
        ]
    },
    # ── 场景5: 退房结算 ──────────────────────────────────────────────────────
    {
        "scene": "checkout",
        "dialogs": [
            {"role": "customer", "content": "我要退房了，订单号BK20260503001，能帮我查下账单吗"},
            {"role": "staff", "content": "好的张先生，账单如下：住宿3晚×398=1194元，加床服务3晚×50=150元，餐饮消费286元，合计1630元，已收押金1000元，需补付630元。"},
            {"role": "customer", "content": "餐饮消费286元是什么，我只吃了早餐"},
            {"role": "staff", "content": "早餐已含房费，这286元是2日晚的逸厨晚餐消费，房间号1806，5月4日19:30刷卡。您确认吗？"},
            {"role": "customer", "content": "对对对，我忘了，没问题。我需要开增值税发票，公司报销"},
            {"role": "staff", "content": "请提供公司名称和税号，发票将在3个工作日内开具并邮寄。押金退回原支付账户，1-3个工作日到账。感谢入住！"},
        ]
    },
]


def ensure_user_exists(base_url: str, user_id: str, db_path: str = None) -> bool:
    """
    Ensure the user exists. Checks via API first; if not found and db_path given,
    creates user directly in SQLite (for local dev/test scenarios).
    """
    resp = requests.get(f"{base_url}/api/v1/memories/", params={"user_id": user_id})
    if resp.status_code == 200:
        return True

    if resp.status_code == 404 and db_path:
        # Create user directly in SQLite (dev/test only)
        import sqlite3
        from uuid import uuid4
        from datetime import datetime
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT OR IGNORE INTO users (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid4()), user_id, f"微信用户-{user_id}", datetime.utcnow().isoformat())
            )
            conn.commit()
            conn.close()
            print(f"  [DB] Created user '{user_id}' directly in SQLite")
            return True
        except Exception as e:
            print(f"  [DB] Failed to create user: {e}")
            return False
    return False


def add_memory(base_url: str, user_id: str, text: str, metadata: dict) -> dict:
    """调用 POST /api/v1/memories/ 写入记忆。"""
    payload = {
        "user_id": user_id,
        "text": text,
        "metadata": metadata,
    }
    resp = requests.post(f"{base_url}/api/v1/memories/", json=payload, timeout=30)
    return {"status": resp.status_code, "body": resp.json() if resp.content else {}}


def search_memories(base_url: str, user_id: str, query: str) -> list:
    """通过 search_query 参数检索相关记忆。"""
    resp = requests.get(
        f"{base_url}/api/v1/memories/",
        params={"user_id": user_id, "search_query": query},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("items", [])
    return []


def seed_conversations(base_url: str, user_id: str, verbose: bool = True):
    """
    将所有场景对话作为记忆写入 OpenMemory，并记录结果。
    返回完整的测试日志列表。
    """
    logs = []

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        logs.append(line)

    log(f"=== 开始写入酒店客服模拟数据 ===")
    log(f"API地址: {base_url}")
    log(f"用户ID: {user_id}")
    log(f"场景数量: {len(HOTEL_CONVERSATIONS)}")
    log("")

    total_written = 0
    total_errors = 0

    for conv in HOTEL_CONVERSATIONS:
        scene = conv["scene"]
        dialogs = conv["dialogs"]
        log(f"── 场景: {scene} ({len(dialogs)} 条对话) ──")

        for i, dialog in enumerate(dialogs):
            role = dialog["role"]
            content = dialog["content"]
            prefix = "👤 客户" if role == "customer" else "🏨 客服"
            log(f"  {prefix}: {content[:60]}{'...' if len(content) > 60 else ''}")

            result = add_memory(
                base_url=base_url,
                user_id=user_id,
                text=f"[{role}] {content}",
                metadata={
                    "source": "wechat",
                    "type": "hotel_consultation",
                    "scene": scene,
                    "role": role,
                    "seeded": True,
                    "dialog_index": i,
                    "timestamp": int(time.time()),
                },
            )

            status = result["status"]
            body = result["body"]
            if status in (200, 201):
                # Count how many memories were created
                n_created = 0
                if isinstance(body, dict) and "results" in body:
                    n_created = len([r for r in body["results"] if r.get("event") == "ADD"])
                elif isinstance(body, list):
                    n_created = len(body)
                log(f"    ✅ HTTP {status} → {n_created} 条记忆写入")
                total_written += 1
            else:
                log(f"    ❌ HTTP {status} → {body}")
                total_errors += 1

            time.sleep(0.1)  # 避免过快请求

        log("")

    log(f"=== 写入完成 ===")
    log(f"成功: {total_written} 条对话, 失败: {total_errors} 条")
    return logs


def run_search_tests(base_url: str, user_id: str) -> list:
    """运行几个搜索测试验证记忆写入正确。"""
    logs = []

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        logs.append(line)

    log("")
    log("=== 搜索验证测试 ===")

    test_queries = [
        ("无烟大床房", "booking"),
        ("游泳池开放时间", "facilities"),
        ("空调噪音投诉", "complaint"),
        ("增值税发票", "checkout"),
        ("押金退款", "checkin"),
    ]

    for query, expected_scene in test_queries:
        results = search_memories(base_url, user_id, query)
        log(f"  🔍 查询: '{query}' → 找到 {len(results)} 条记忆")
        for mem in results[:2]:  # 展示前2条
            content = mem.get("content", "")[:80]
            cats = mem.get("categories", [])
            log(f"     · {content}  [分类: {', '.join(cats)}]")
        if not results:
            log(f"     ⚠️  未找到相关记忆 (注: mock模式下向量搜索可能返回空)")

    return logs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="酒店客服数据种子脚本")
    parser.add_argument("--host", default="http://localhost:8765", help="API地址")
    parser.add_argument("--user", default="hotel_guest", help="用户ID (默认使用已存在的 hotel_guest)")
    parser.add_argument("--db", default="./api/openmemory.db", help="SQLite DB路径（用于自动建用户）")
    parser.add_argument("--search-only", action="store_true", help="仅运行搜索测试")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  OpenMemory 酒店客服场景测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    if not args.search_only:
        ok = ensure_user_exists(args.host, args.user, db_path=args.db)
        if not ok:
            print(f"⚠️  用户 '{args.user}' 不存在且无法创建，请先确认用户或提供 --db 路径")
            exit(1)
        seed_logs = seed_conversations(args.host, args.user)
    else:
        seed_logs = []

    search_logs = run_search_tests(args.host, args.user)

    print(f"\n{'='*60}")
    print(f"  测试完成")
    print(f"{'='*60}\n")
