import { useState, type FormEvent } from "react";
import { MessageCircle, X, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export function ChatWidget() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", text: "Hi! Ask me about product prices, availability, or your order status." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  if (!user) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setSending(true);

    try {
      const res = await api.post<{ reply: string }>("/api/ai/chat", { message: text });
      setMessages((prev) => [...prev, { role: "assistant", text: res.data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, I couldn't reach the support agent. Please try again." },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-20">
      {open ? (
        <div className="w-80 h-96 bg-background border rounded-lg shadow-lg flex flex-col">
          <div className="flex items-center justify-between border-b p-3">
            <span className="font-medium text-sm">AI Support Agent</span>
            <button onClick={() => setOpen(false)} aria-label="Close chat">
              <X className="size-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "text-right"
                    : "text-left text-muted-foreground"
                }
              >
                <span
                  className={
                    m.role === "user"
                      ? "inline-block bg-primary text-primary-foreground rounded-lg px-3 py-1.5"
                      : "inline-block bg-muted rounded-lg px-3 py-1.5"
                  }
                >
                  {m.text}
                </span>
              </div>
            ))}
            {sending && <div className="text-muted-foreground text-xs">Thinking...</div>}
          </div>
          <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t p-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about products or orders..."
              className="text-sm"
            />
            <Button type="submit" size="icon" disabled={sending}>
              <Send className="size-4" />
            </Button>
          </form>
        </div>
      ) : (
        <Button size="icon" className="size-12 rounded-full shadow-lg" onClick={() => setOpen(true)}>
          <MessageCircle className="size-6" />
        </Button>
      )}
    </div>
  );
}
