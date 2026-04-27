"""
Simple chat router for demo/mock mode.
Uses keyword search over pre-seeded hotel consultation memories.
No API key required.
"""
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Memory, MemoryState
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = []


HOTEL_GREETINGS = ["你好", "hi", "hello", "您好", "在吗", "咨询"]
HOTEL_KEYWORDS = {
    "房间": ["客房", "标准间", "大床房", "双床房", "套房", "豪华", "房型", "住宿", "房价"],
    "价格": ["多少钱", "费用", "收费", "报价", "优惠", "折扣", "价格", "房费"],
    "早餐": ["早餐", "餐饮", "用餐", "包餐", "自助餐"],
    "停车": ["停车", "泊车", "车位", "停车场", "泊位"],
    "入住": ["入住", "办理", "checkin", "check-in", "几点"],
    "退房": ["退房", "checkout", "check-out", "晚退", "延迟"],
    "设施": ["健身", "游泳", "泳池", "spa", "会议室", "商务", "设施", "服务"],
    "预订": ["预订", "预定", "订房", "订单", "取消", "退款"],
    "位置": ["位置", "地址", "地点", "怎么走", "附近", "交通", "打车"],
    "发票": ["发票", "收据", "报销", "税票"],
}

HOTEL_RESPONSES = {
    "房间": """我们酒店提供以下房型：
🏨 **标准大床房**：168元/晚，面积28㎡，1.8m大床
🏨 **标准双床房**：178元/晚，面积28㎡，两张1.2m床
🏨 **豪华大床房**：258元/晚，面积38㎡，含城市景观
🏨 **商务套房**：388元/晚，面积55㎡，独立客厅

所有房型均含免费WiFi，欢迎预订！""",

    "价格": """我们的房价如下：
- 标准间：168-178元/晚
- 豪华间：258元/晚
- 套房：388元起/晚

🎉 **当前优惠**：提前7天预订享9折优惠，会员享8.5折！
连住3晚以上还有额外折扣，详情可咨询前台。""",

    "早餐": """关于早餐：
🍳 早餐时间：**7:00-9:30**
🍳 地点：一楼餐厅（逸厨餐厅）
🍳 形式：中西式自助早餐
💰 房间含早餐：额外加收38元/人/天（已含早餐的套餐除外）

早餐品种丰富，包括粥品、面点、西式烤制品、水果、饮品等。""",

    "停车": """关于停车：
🚗 我们提供地下停车场，共200个车位
💰 停车费：**免费**（住店期间）
🕐 出入口24小时开放
📍 停车场入口在酒店北侧

如有大型车辆需提前告知，我们将安排合适车位。""",

    "入住": """入住须知：
✅ **标准入住时间**：14:00
✅ **早入住**：可提前申请，视房间情况，12:00前入住加收半天房费
✅ **需携带**：本人有效身份证件
✅ **押金**：200元（入住时收取，退房退还）

如提前到达，可以先存放行李，在大堂休息。""",

    "退房": """退房须知：
🕐 **标准退房时间**：12:00
🕐 **延迟退房**：可申请延至14:00，免费；14:00-18:00加收半天房费；18:00后按全天计算
📞 退房前请拨打前台电话或直接前往前台办理

退房时请归还房卡，我们将检查房间并退还押金。""",

    "设施": """酒店设施介绍：
🏊 **游泳池**：6:00-22:00，免费对住客开放
💪 **健身房**：全天开放，免费
🧖 **SPA中心**：9:00-21:00，独立收费
🎯 **会议室**：可容纳20-200人，需提前预订
🎮 **儿童乐园**：9:00-20:00，免费
☕ **商务中心**：24小时，免费打印复印""",

    "预订": """关于预订：
📱 **预订方式**：
  - 微信直接联系我们
  - 拨打前台电话：0571-8888-9999
  - 登录官网在线预订
  
✅ **预订确认**：下单后2小时内确认
❌ **取消政策**：入住前48小时取消免费；48小时内取消收取首晚房费

欢迎提前预订，节假日需提早2周以上。""",

    "位置": """酒店位置信息：
📍 **地址**：浙江省杭州市西湖区文三路888号
🚇 **地铁**：2号线文三路站A出口步行3分钟
🚌 **公交**：文三路上约12路、52路、K599路等
🚕 **打车**：从火车站约20分钟，机场约45分钟
🅿️ 停车免费

酒店对面是文三数字生活街区，购物餐饮非常方便！""",

    "发票": """关于发票：
🧾 **发票类型**：增值税普通发票或专用发票
🧾 **开具时间**：退房时或退房后7个工作日内
🧾 **抬头**：可开具个人或公司抬头
📧 电子发票可发送至您的邮箱

需要专票请提前告知，需提供公司全称、税号、地址电话及开户行信息。""",
}

DEFAULT_RESPONSE = """您好，感谢联系杭州逸景酒店！🏨

我可以为您解答以下问题：
- 🏨 **房型介绍** - 查询各类房型和价格
- 🕐 **入住/退房** - 时间安排和注意事项
- 🍳 **早餐服务** - 用餐时间和费用
- 🚗 **停车服务** - 停车费用和位置
- 🏊 **酒店设施** - 游泳池、健身房等
- 📱 **预订咨询** - 如何预订和取消政策
- 📍 **酒店位置** - 地址和交通方式
- 🧾 **发票须知** - 开具发票相关

请问您想了解哪方面的信息？"""


def _keyword_match(message: str) -> Optional[str]:
    """Simple keyword-based response matching."""
    message_lower = message.lower()
    
    # Check greetings
    for greet in HOTEL_GREETINGS:
        if greet in message_lower:
            return DEFAULT_RESPONSE
    
    # Check categories
    for category, keywords in HOTEL_KEYWORDS.items():
        for kw in keywords:
            if kw in message_lower:
                return HOTEL_RESPONSES.get(category, DEFAULT_RESPONSE)
    
    return None


def _search_memories(message: str, db: Session) -> List[str]:
    """Search active memories for relevant content."""
    keywords = re.findall(r'[\u4e00-\u9fff]{2,}|\w{3,}', message)
    sources = []
    
    for kw in keywords[:3]:
        memories = (
            db.query(Memory)
            .filter(
                Memory.state == MemoryState.active,
                Memory.content.contains(kw)
            )
            .limit(3)
            .all()
        )
        for m in memories:
            if m.content not in sources:
                sources.append(m.content)
    
    return sources[:5]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Simple chat endpoint for hotel consultation demo."""
    message = request.message.strip()
    if not message:
        return ChatResponse(reply="请输入您的问题 😊", sources=[])
    
    # Try keyword-based response first
    reply = _keyword_match(message)
    
    # Search memories for context
    sources = _search_memories(message, db)
    
    if reply is None:
        if sources:
            reply = f"根据我们的记录，为您找到以下相关信息：\n\n"
            for i, s in enumerate(sources[:3], 1):
                reply += f"{i}. {s}\n\n"
            reply += "如需了解更多，请继续提问！"
        else:
            reply = DEFAULT_RESPONSE
    
    return ChatResponse(reply=reply, sources=sources)


@router.get("/history", response_model=List[dict])
async def get_sample_conversations():
    """Return sample WeChat hotel consultation conversations."""
    return [
        {
            "id": 1,
            "timestamp": "2024-01-15 09:23",
            "customer": "请问你们有标准间吗？多少钱一晚？",
            "reply": "您好！我们标准大床房168元/晚，标准双床房178元/晚，都含免费WiFi，欢迎预订！"
        },
        {
            "id": 2,
            "timestamp": "2024-01-15 10:45",
            "customer": "停车要收费吗",
            "reply": "住店期间停车完全免费，地下停车场200个车位，24小时开放，入口在酒店北侧。"
        },
        {
            "id": 3,
            "timestamp": "2024-01-15 14:30",
            "customer": "早餐几点开始，多少钱",
            "reply": "早餐时间7:00-9:30，一楼逸厨餐厅，中西式自助，加收38元/人。"
        },
        {
            "id": 4,
            "timestamp": "2024-01-16 08:00",
            "customer": "下午两点能入住吗",
            "reply": "标准入住时间14:00，您2点完全没问题！记得带身份证，押金200元。"
        },
        {
            "id": 5,
            "timestamp": "2024-01-16 11:50",
            "customer": "能延迟退房吗，我想多住两个小时",
            "reply": "可以！12:00-14:00延迟退房免费，需提前告知前台。"
        }
    ]
