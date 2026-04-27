"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, MessageCircle, History } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  timestamp: string;
}

interface SampleConversation {
  id: number;
  timestamp: string;
  customer: string;
  reply: string;
}

const QUICK_QUESTIONS = [
  "标准间多少钱一晚？",
  "有停车位吗？免费吗？",
  "早餐几点开始？",
  "几点可以入住？",
  "有游泳池吗？",
  "怎么预订房间？",
  "酒店在哪里？",
  "可以开发票吗？",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "您好！欢迎咨询杭州逸景酒店 🏨\n\n我是您的智能客服，可以为您解答关于房型、价格、设施、预订等问题。请问有什么可以帮您？",
      timestamp: new Date().toLocaleTimeString("zh-CN"),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sampleConvos, setSampleConvos] = useState<SampleConversation[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history`)
      .then((r) => r.json())
      .then(setSampleConvos)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const messageText = (text || input).trim();
    if (!messageText || loading) return;

    const userMsg: Message = {
      role: "user",
      content: messageText,
      timestamp: new Date().toLocaleTimeString("zh-CN"),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageText,
          history: messages.slice(-6).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      const data = await res.json();
      const assistantMsg: Message = {
        role: "assistant",
        content: data.reply || "抱歉，暂时无法回答，请稍后再试。",
        sources: data.sources,
        timestamp: new Date().toLocaleTimeString("zh-CN"),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "连接服务器失败，请检查后端是否已启动。",
          timestamp: new Date().toLocaleTimeString("zh-CN"),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const formatContent = (content: string) => {
    return content.split("\n").map((line, i) => (
      <span key={i}>
        {line
          .split(/(\*\*[^*]+\*\*)/)
          .map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <strong key={j}>{part.slice(2, -2)}</strong>
            ) : (
              part
            )
          )}
        {i < content.split("\n").length - 1 && <br />}
      </span>
    ));
  };

  return (
    <div className="container py-6 h-[calc(100vh-80px)] flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
            <MessageCircle className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">
              杭州逸景酒店 · 微信客服
            </h1>
            <p className="text-sm text-zinc-400">
              酒店咨询智能助手 · 模拟微信聊天记录
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowHistory(!showHistory)}
          className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
        >
          <History className="w-4 h-4 mr-1" />
          历史对话
        </Button>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Chat window */}
        <div className="flex-1 flex flex-col bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 ${
                  msg.role === "user" ? "flex-row-reverse" : ""
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.role === "user"
                      ? "bg-zinc-700"
                      : "bg-blue-600"
                  }`}
                >
                  {msg.role === "user" ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>
                <div
                  className={`max-w-[75%] ${
                    msg.role === "user" ? "items-end" : "items-start"
                  } flex flex-col gap-1`}
                >
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-sm"
                        : "bg-zinc-800 text-zinc-100 rounded-tl-sm"
                    }`}
                  >
                    {formatContent(msg.content)}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="text-xs text-zinc-500 max-w-full">
                      <details>
                        <summary className="cursor-pointer hover:text-zinc-400">
                          📚 相关记忆 ({msg.sources.length})
                        </summary>
                        <ul className="mt-1 space-y-1">
                          {msg.sources.map((s, j) => (
                            <li
                              key={j}
                              className="bg-zinc-800/50 rounded px-2 py-1 text-zinc-400"
                            >
                              {s}
                            </li>
                          ))}
                        </ul>
                      </details>
                    </div>
                  )}
                  <span className="text-xs text-zinc-600">{msg.timestamp}</span>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-zinc-800 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1 items-center">
                    <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Quick questions */}
          <div className="px-4 py-2 border-t border-zinc-800">
            <div className="flex gap-2 flex-wrap">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={loading}
                  className="text-xs px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-4 border-t border-zinc-800 flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="输入您的问题，如：有哪些房型？停车费多少？"
              className="flex-1 bg-zinc-800 text-white rounded-lg px-4 py-2.5 text-sm outline-none border border-zinc-700 focus:border-blue-500 placeholder:text-zinc-500"
              disabled={loading}
            />
            <Button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* History sidebar */}
        {showHistory && (
          <div className="w-72 bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col overflow-hidden">
            <div className="p-3 border-b border-zinc-800">
              <h3 className="text-sm font-medium text-white">微信客服历史对话</h3>
              <p className="text-xs text-zinc-500 mt-0.5">真实酒店咨询记录</p>
            </div>
            <ScrollArea className="flex-1 p-3">
              <div className="space-y-3">
                {sampleConvos.map((c) => (
                  <div
                    key={c.id}
                    className="bg-zinc-800 rounded-lg p-3 space-y-2 cursor-pointer hover:bg-zinc-700 transition-colors"
                    onClick={() => sendMessage(c.customer)}
                  >
                    <p className="text-xs text-zinc-500">{c.timestamp}</p>
                    <div className="flex gap-2">
                      <span className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded">
                        客户
                      </span>
                      <p className="text-xs text-zinc-300">{c.customer}</p>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-xs bg-green-900/50 text-green-300 px-1.5 py-0.5 rounded">
                        回复
                      </span>
                      <p className="text-xs text-zinc-400 line-clamp-2">
                        {c.reply}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}
