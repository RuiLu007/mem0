"""
Seed hotel consultation WeChat chat records into the database.
Injects memories directly without requiring an LLM API key.
"""
import datetime
import sys
import uuid

sys.path.insert(0, "/root/01userprofile_ai/mem0/openmemory/api")

from app.database import Base, SessionLocal, engine
from app.models import App, Memory, MemoryState, User

HOTEL_MEMORIES = [
    # Room related
    "客户询问标准大床房价格，我们报价168元/晚，面积28平，1.8米大床，含WiFi",
    "客户询问双床房，报价178元/晚，适合家庭或朋友出行，两张1.2米床",
    "豪华大床房258元/晚，38平，可欣赏城市景观，包含欢迎水果",
    "商务套房388元/晚，55平，独立客厅，适合商务出行客人",
    "节假日特惠：元旦三天连住优惠，标准间降至150元/晚",
    # Breakfast
    "早餐时间7:00-9:30，一楼逸厨餐厅，中西式自助，加收38元/人/天",
    "客户问早餐是否包含在房价内：默认不含，可在预订时选择含早方案",
    "早餐品种：粥品、面点、包子、西式烤制品、各类水果和饮品",
    # Parking
    "停车场在酒店地下，住店期间完全免费，共200个车位",
    "停车场入口在酒店北侧，24小时开放，大型车辆需提前告知",
    "外来访客停车：前2小时免费，之后5元/小时",
    # Check-in/out
    "标准入住时间14:00，早入住12:00前需加收半天房费（视房间情况）",
    "退房时间12:00，延迟至14:00免费，14:00-18:00加收半天，18:00后全天",
    "入住需要本人有效身份证，押金200元，退房时退还",
    "客户问能否提前到店存行李：可以，大堂提供行李寄存服务",
    # Facilities
    "游泳池对住客免费开放，时间6:00-22:00，儿童游泳需家长陪同",
    "健身房24小时开放，住客免费使用，配备跑步机、哑铃等器械",
    "SPA中心9:00-21:00，提供按摩、护理等项目，独立收费",
    "会议室可容纳20-200人，需提前预订，设备齐全含投影仪和音响",
    "商务中心24小时开放，提供免费打印复印服务",
    # Booking and cancellation
    "预订方式：微信咨询、官网预订或拨打前台电话0571-8888-9999",
    "取消政策：入住前48小时免费取消；48小时内取消收首晚房费",
    "提前7天预订享9折优惠，会员享8.5折，连住3晚以上额外折扣",
    "节假日订房需提前2周，五一、国庆需提前1个月",
    "客户取消了元旦订单，入住前72小时，按政策全额退款",
    # Location & transport
    "酒店地址：浙江省杭州市西湖区文三路888号",
    "地铁2号线文三路站A出口步行3分钟即到",
    "打车从杭州东站约20分钟，从萧山机场约45分钟",
    "酒店对面是文三数字生活街区，购物餐饮非常方便",
    # Invoice
    "发票可开具增值税普通发票或专用发票，退房时或7个工作日内",
    "企业报销需专票：提供公司名称、税号、地址电话、开户行信息",
    "电子发票可发送至客户邮箱，纸质发票现场领取",
    # Special requests
    "客户请求高楼层房间，已安排28楼景观大床房，俯瞰西湖方向",
    "客户需要加床：豪华间可加一张折叠床，加收50元/晚",
    "客户请求无烟房：我们所有楼层均为无烟环境，违规扣押金",
    "客户问是否宠物友好：酒店不允许携带宠物入住",
    "有客人要求叫早服务：前台提供叫早服务，也可设置房间内电话叫醒",
    # Complaints/feedback
    "2024-01-20 客户反馈房间隔音效果不好，已更换至高楼层安静房间，客户满意",
    "客户投诉早餐品种减少，已反馈餐饮部，增加了两种粥品和点心",
    "客户表扬前台工作人员小李服务热情专业，已录入员工表彰记录",
]

WECHAT_CONVERSATIONS = [
    "微信客服对话记录：客户张女士询问520情人节特惠，推荐了豪华大床房含早双人套餐398元",
    "微信客服：李先生商务出差，需要会议室半天+3间商务间，已报价并预订成功",
    "微信群接龙：20人公司年会，预订了天际宴会厅，含自助晚宴和客房15间",
    "微信咨询：王先生问地铁怎么到酒店，告知2号线文三路站A口出步行3分钟",
    "微信退订：陈女士因疫情影响取消暑期订单，入住前72小时，全额退款已处理",
    "微信好评截图：刘先生一家三口入住，孩子喜欢儿童乐园，五星好评",
    "微信问询：赵小姐问SPA是否需要提前预约，告知提前1天预约更稳妥",
    "微信投诉转处理：孙先生订房后当天无法入住，已协调调至次日并补偿早餐券2张",
]


def seed_database():
    db = SessionLocal()
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        user_id = "hotel_guest"
        
        # Get or create user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                user_id=user_id,
                name="酒店咨询用户",
                created_at=datetime.datetime.now(datetime.UTC)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created user: {user_id}")
        else:
            print(f"✅ User exists: {user_id}")

        # Get or create app
        app = db.query(App).filter(
            App.name == "openmemory",
            App.owner_id == user.id
        ).first()
        if not app:
            app = App(
                id=uuid.uuid4(),
                name="openmemory",
                owner_id=user.id,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            print(f"✅ Created app: openmemory")
        else:
            print(f"✅ App exists: openmemory")

        # Check existing memories
        existing_count = db.query(Memory).filter(
            Memory.user_id == user.id,
            Memory.app_id == app.id
        ).count()
        
        if existing_count > 0:
            print(f"ℹ️  {existing_count} memories already exist, skipping seed")
            return

        # Seed all hotel memories
        all_memories = HOTEL_MEMORIES + WECHAT_CONVERSATIONS
        count = 0
        for content in all_memories:
            memory = Memory(
                id=uuid.uuid4(),
                user_id=user.id,
                app_id=app.id,
                content=content,
                metadata_={
                    "source": "wechat",
                    "type": "hotel_consultation",
                    "seeded": True
                },
                state=MemoryState.active,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
            )
            db.add(memory)
            count += 1

        db.commit()
        print(f"✅ Seeded {count} hotel consultation memories")
        print("   包含：房型价格、早餐、停车、入住退房、设施、预订、位置、发票、微信对话记录")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
