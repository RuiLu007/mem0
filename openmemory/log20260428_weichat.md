# log20260428_weichat.md — 企业微信集成接入指南

> 版本：2026-04-28  
> 目标：将企业微信聊天数据（会话内容存档）接入 OpenMemory 系统，实现客服对话的自动记忆化

---

## 一、整体集成架构

```
企业微信后台
    │  会话内容存档 (加密推送)
    ▼
┌─────────────────────────────────────────────────────┐
│  WeCom Sync Service  (Python 采集服务)               │
│  wecom_sync.py                                       │
│  ① 调用 get_msg_list API 拉取加密消息                 │
│  ② 使用 WXBizMsgCrypt 解密                           │
│  ③ 过滤/清洗文本消息                                  │
│  ④ 调用 OpenMemory API 存入记忆                       │
└─────────────────────────────────────────────────────┘
    │  POST /api/v1/memories/
    ▼
┌─────────────────────────────────────────────────────┐
│  OpenMemory FastAPI 后端  :8765                      │
│  → mem0 FAISS 向量存储                               │
│  → SQLite 记忆元数据                                  │
└─────────────────────────────────────────────────────┘
    │  查询记忆
    ▼
┌─────────────────────────────────────────────────────┐
│  聊天/问答前端  :3000                                 │
│  基于历史记忆为客服提供上下文参考                       │
└─────────────────────────────────────────────────────┘
```

---

## 二、企业微信后台准备工作

### 2.1 申请会话内容存档权限

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin)
2. 进入：**应用管理 → 会话内容存档**
3. 点击"开启会话存档"并阅读协议
4. 申请权限后，企业微信审核（通常 1-3 个工作日）

### 2.2 获取必要密钥和配置

进入**会话内容存档**页面，记录以下信息：

| 配置项 | 说明 | 存储位置 |
|--------|------|---------|
| `corpid` | 企业 ID | 管理后台首页 |
| `SECRET` | 会话存档应用 Secret | 应用管理 → 会话存档 → Secret |
| `RSA 私钥` | 解密消息体用 | 自行生成，公钥上传至后台 |

### 2.3 生成 RSA 密钥对

```bash
# 生成 2048 位 RSA 私钥
openssl genrsa -out wecom_private_key.pem 2048

# 提取公钥（上传至企业微信后台）
openssl rsa -in wecom_private_key.pem -pubout -out wecom_public_key.pem

# 查看公钥内容（复制粘贴到企业微信后台）
cat wecom_public_key.pem
```

### 2.4 配置 IP 白名单

在企业微信后台：**会话内容存档 → 安全配置 → IP 白名单**  
添加运行本采集服务的服务器 IP。

### 2.5 安装企业微信官方 SDK

企业微信会话存档需要使用官方提供的 C SDK（`libWeWorkFinanceSdk_C.so`）：

```bash
# 下载官方 SDK（需在企业微信开发者文档中申请下载权限）
# 文档地址：https://developer.work.weixin.qq.com/document/path/91774

# 将 .so 文件放到项目目录
mkdir -p wecom_sdk
# 拷贝 libWeWorkFinanceSdk_C.so 到 wecom_sdk/
```

---

## 三、Python 依赖安装

```bash
pip install requests python-dotenv cryptography
# 如需解析企业微信 XML 消息
pip install xmltodict
```

---

## 四、环境变量配置

创建 `wecom_sync/.env`：

```env
# 企业微信配置
WECOM_CORPID=ww你的企业ID
WECOM_SECRET=你的会话存档Secret
WECOM_RSA_PRIVATE_KEY_PATH=./wecom_sdk/wecom_private_key.pem

# OpenMemory 接口
OPENMEMORY_API_URL=http://localhost:8765
OPENMEMORY_USER_ID=wecom_sync

# 同步配置
WECOM_SDK_PATH=./wecom_sdk/libWeWorkFinanceSdk_C.so
SYNC_INTERVAL_SECONDS=60      # 每隔 60 秒拉取一次
SYNC_FROM_SEQ=0               # 起始消息序号（0 = 从头开始）
```

---

## 五、Python 实现代码

### 5.1 目录结构

```
wecom_sync/
├── .env
├── wecom_private_key.pem
├── libWeWorkFinanceSdk_C.so      ← 企业微信官方 SDK
├── wecom_sdk_wrapper.py          ← SDK C 函数封装
├── wecom_sync.py                 ← 主同步逻辑
└── openmemory_client.py          ← OpenMemory API 客户端
```

### 5.2 SDK 封装层  `wecom_sdk_wrapper.py`

```python
"""
企业微信会话内容存档 C SDK Python 封装。
官方 SDK 文档：https://developer.work.weixin.qq.com/document/path/91774
"""
import ctypes
import json
import os
from pathlib import Path
from typing import List, Dict


class WeComSDK:
    """封装企业微信官方 libWeWorkFinanceSdk_C.so"""

    def __init__(self, sdk_path: str = None):
        path = sdk_path or os.environ.get(
            "WECOM_SDK_PATH", "./wecom_sdk/libWeWorkFinanceSdk_C.so"
        )
        self._lib = ctypes.CDLL(path)
        self._setup_signatures()

    def _setup_signatures(self):
        """设置 C 函数类型签名"""
        lib = self._lib

        # NewSdk() -> void*
        lib.NewSdk.restype = ctypes.c_void_p

        # Init(sdk, corpid, secret) -> int
        lib.Init.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.Init.restype = ctypes.c_int

        # GetChatData(sdk, seq, limit, proxy, passwd, timeout, slice) -> int
        lib.GetChatData.argtypes = [
            ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_uint,
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p
        ]
        lib.GetChatData.restype = ctypes.c_int

        # DecryptData(sdk, key, encrypt_msg, msg) -> int
        lib.DecryptData.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p
        ]
        lib.DecryptData.restype = ctypes.c_int

        # GetContentFromSlice(slice) -> char*
        lib.GetContentFromSlice.argtypes = [ctypes.c_void_p]
        lib.GetContentFromSlice.restype = ctypes.c_char_p

        # NewSlice() -> void* / FreeSlice(slice)
        lib.NewSlice.restype = ctypes.c_void_p
        lib.FreeSlice.argtypes = [ctypes.c_void_p]

        # FreeSdk(sdk)
        lib.FreeSdk.argtypes = [ctypes.c_void_p]

    def get_messages(
        self,
        corpid: str,
        secret: str,
        private_key: str,
        from_seq: int = 0,
        limit: int = 100,
    ) -> List[Dict]:
        """
        拉取并解密企业微信会话消息。

        Returns:
            list of message dicts（已解密，原始 JSON 结构）
        """
        sdk = self._lib.NewSdk()
        try:
            ret = self._lib.Init(
                sdk, corpid.encode(), secret.encode()
            )
            if ret != 0:
                raise RuntimeError(f"WeComSDK Init failed: code={ret}")

            slice_ = self._lib.NewSlice()
            try:
                ret = self._lib.GetChatData(
                    sdk, from_seq, limit, b"", b"", 15, slice_
                )
                if ret != 0:
                    raise RuntimeError(f"GetChatData failed: code={ret}")

                raw = self._lib.GetContentFromSlice(slice_)
                chat_list = json.loads(raw.decode("utf-8"))
            finally:
                self._lib.FreeSlice(slice_)

            messages = []
            for item in chat_list.get("chatdata", []):
                # 解密单条消息
                msg_slice = self._lib.NewSlice()
                try:
                    ret = self._lib.DecryptData(
                        sdk,
                        private_key.encode(),
                        item["encrypt_random_msg"].encode(),
                        msg_slice,
                    )
                    if ret == 0:
                        msg_raw = self._lib.GetContentFromSlice(msg_slice)
                        msg = json.loads(msg_raw.decode("utf-8"))
                        msg["_seq"] = item["seq"]
                        messages.append(msg)
                finally:
                    self._lib.FreeSlice(msg_slice)

            return messages
        finally:
            self._lib.FreeSdk(sdk)
```

### 5.3 OpenMemory 客户端  `openmemory_client.py`

```python
"""OpenMemory REST API 简单客户端"""
import os
import requests
from typing import Optional


class OpenMemoryClient:
    def __init__(self, base_url: str = None, user_id: str = None):
        self.base_url = (base_url or os.environ.get(
            "OPENMEMORY_API_URL", "http://localhost:8765"
        )).rstrip("/")
        self.user_id = user_id or os.environ.get("OPENMEMORY_USER_ID", "wecom_sync")

    def add_memory(self, text: str, metadata: Optional[dict] = None) -> dict:
        """向 OpenMemory 添加一条记忆"""
        payload = {
            "text": text,
            "user_id": self.user_id,
            "app_id": "wecom",
            "metadata": metadata or {},
        }
        resp = requests.post(f"{self.base_url}/api/v1/memories/", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_memory(self, query: str, limit: int = 5) -> list:
        """搜索相关记忆"""
        params = {"query": query, "user_id": self.user_id, "limit": limit}
        resp = requests.get(f"{self.base_url}/api/v1/memories/search", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
```

### 5.4 主同步服务  `wecom_sync.py`

```python
"""
企业微信会话内容存档 → OpenMemory 同步服务

运行：
    python wecom_sync.py
    python wecom_sync.py --once      # 只同步一次，不循环
"""
import argparse
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

from wecom_sdk_wrapper import WeComSDK
from openmemory_client import OpenMemoryClient


# ── 配置 ──────────────────────────────────────────────────────────
CORPID       = os.environ["WECOM_CORPID"]
SECRET       = os.environ["WECOM_SECRET"]
PRIVATE_KEY  = Path(os.environ["WECOM_RSA_PRIVATE_KEY_PATH"]).read_text()
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", 60))

# 持久化当前同步进度（断点续传）
SEQ_FILE = Path(__file__).parent / ".sync_seq"


def load_seq() -> int:
    if SEQ_FILE.exists():
        return int(SEQ_FILE.read_text().strip())
    return int(os.environ.get("SYNC_FROM_SEQ", 0))


def save_seq(seq: int):
    SEQ_FILE.write_text(str(seq))


def msg_to_memory_text(msg: dict) -> str:
    """
    将企业微信消息转为适合存入 OpenMemory 的文本。
    根据消息类型（text/voice/file 等）提取关键信息。
    """
    msgtype = msg.get("msgtype", "unknown")
    sender = msg.get("from", "unknown")
    room = msg.get("roomid", "")
    tolist = ", ".join(msg.get("tolist", []))

    if msgtype == "text":
        content = msg.get("text", {}).get("content", "")
    elif msgtype == "voice":
        content = "[语音消息]"
    elif msgtype == "image":
        content = "[图片消息]"
    elif msgtype == "file":
        fname = msg.get("file", {}).get("filename", "")
        content = f"[文件: {fname}]"
    elif msgtype == "link":
        title = msg.get("link", {}).get("title", "")
        content = f"[链接: {title}]"
    else:
        content = f"[{msgtype}消息]"

    parts = [f"发送人: {sender}"]
    if room:
        parts.append(f"群聊: {room}")
    parts.append(f"接收人: {tolist}")
    parts.append(f"内容: {content}")
    return "\n".join(parts)


def sync_once(sdk: WeComSDK, client: OpenMemoryClient) -> int:
    """
    执行一次同步，返回本次同步的消息数量。
    """
    seq = load_seq()
    print(f"[sync] 从 seq={seq} 开始拉取...")

    messages = sdk.get_messages(
        corpid=CORPID,
        secret=SECRET,
        private_key=PRIVATE_KEY,
        from_seq=seq,
        limit=100,
    )

    if not messages:
        print("[sync] 暂无新消息")
        return 0

    synced = 0
    max_seq = seq

    for msg in messages:
        try:
            # 只处理文本类消息（可按需扩展）
            if msg.get("msgtype") not in ("text", "voice", "image", "file", "link"):
                continue

            text = msg_to_memory_text(msg)
            metadata = {
                "source": "wecom",
                "msgtype": msg.get("msgtype"),
                "from": msg.get("from"),
                "roomid": msg.get("roomid", ""),
                "msgtime": msg.get("msgtime", ""),
                "seq": msg.get("_seq", 0),
            }

            client.add_memory(text, metadata=metadata)
            synced += 1
            max_seq = max(max_seq, msg.get("_seq", 0))
            print(f"  ✓ 存入记忆: {text[:60]}...")

        except Exception as e:
            print(f"  ✗ 处理消息失败: {e}")

    # 保存进度
    save_seq(max_seq + 1)
    print(f"[sync] 本次同步 {synced} 条，下次从 seq={max_seq + 1} 开始")
    return synced


def main():
    parser = argparse.ArgumentParser(description="企业微信 → OpenMemory 同步服务")
    parser.add_argument("--once", action="store_true", help="只同步一次后退出")
    args = parser.parse_args()

    sdk = WeComSDK()
    client = OpenMemoryClient()

    print(f"🚀 WeCom Sync 启动 (corpid={CORPID[:6]}...)")
    print(f"   OpenMemory: {client.base_url}")
    print(f"   同步间隔: {SYNC_INTERVAL}s")

    if args.once:
        sync_once(sdk, client)
        return

    while True:
        try:
            sync_once(sdk, client)
        except Exception as e:
            print(f"[ERROR] 同步异常: {e}")
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
```

---

## 六、启动同步服务

```bash
cd wecom_sync/

# 测试单次同步
python wecom_sync.py --once

# 持续运行（后台）
nohup python wecom_sync.py > wecom_sync.log 2>&1 &
echo "同步服务 PID: $!"

# 查看日志
tail -f wecom_sync.log
```

---

## 七、验证集成效果

```bash
# 查询同步进来的消息记忆
curl -s "http://localhost:8765/api/v1/memories/?user_id=wecom_sync&page=1&page_size=10" \
  | python3 -m json.tool

# 搜索特定话题
curl -s "http://localhost:8765/api/v1/memories/search?query=客房投诉&user_id=wecom_sync" \
  | python3 -m json.tool
```

---

## 八、注意事项

| 事项 | 说明 |
|------|------|
| 数据合规 | 会话存档须征得员工同意，需在企业制度中明确告知 |
| 密钥安全 | `WECOM_SECRET` 和 RSA 私钥不得提交到 Git，务必加入 `.gitignore` |
| SDK 版本 | 官方 SDK 会更新，请关注企业微信开发者文档 |
| 消息去重 | `_seq` 字段递增，同步进度保存在 `.sync_seq` 文件中实现断点续传 |
| 限流 | 企业微信 API 有频率限制，建议 `SYNC_INTERVAL_SECONDS >= 60` |
| 私聊 vs 群聊 | `roomid` 为空 = 私聊，非空 = 群聊，可按需过滤 |

---

## 九、企业微信开发文档参考

- 会话内容存档 API：https://developer.work.weixin.qq.com/document/path/91774
- 企业微信 SDK 下载：https://developer.work.weixin.qq.com/document/path/91774#%E8%B5%84%E6%BA%90%E4%B8%8B%E8%BD%BD
- 消息类型说明：https://developer.work.weixin.qq.com/document/path/91774#%E6%B6%88%E6%81%AF%E7%B1%BB%E5%9E%8B
