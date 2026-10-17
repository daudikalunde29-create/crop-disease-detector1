import { useEffect, useState, useRef } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useServerFn } from "@tanstack/react-start";
import { supabase } from "@/integrations/supabase/client";
import { getAssistantHistory } from "@/lib/assistant/history.functions";
import { Conversation, ConversationContent, ConversationScrollButton } from "@/components/ai-elements/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { PromptInput, PromptInputTextarea, PromptInputFooter, PromptInputSubmit } from "@/components/ai-elements/prompt-input";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export function CropAssistant() {
  const loadHistory = useServerFn(getAssistantHistory);
  const [state, setState] = useState<{ userId: string; messages: UIMessage[] } | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const { data } = await supabase.auth.getUser();
        if (!data.user) { if (active) setNotice("Please sign in to chat with Crop Assistant."); return; }
        const messages = await loadHistory();
        if (active) setState({ userId: data.user.id, messages: messages as unknown as UIMessage[] });
      } catch { if (active) setNotice("Your conversation could not be loaded. Please reopen the assistant to try again."); }
      finally { if (active) setLoading(false); }
    }
    void load();
    return () => { active = false; };
  }, [loadHistory]);
  return <div className="crop-assistant flex h-dvh flex-col bg-background text-foreground">
    <header className="flex shrink-0 items-center justify-between border-b border-border p-4">
      <div className="flex items-center gap-3"><img src="/site/assets/images/crop-assistant.svg" alt="" className="size-10" /><div><h1 className="text-base font-semibold">Crop Assistant</h1><p className="text-xs text-muted-foreground">English · Kiswahili</p></div></div>
      <Button size="icon-sm" variant="ghost" title="Close assistant" aria-label="Close assistant" onClick={() => window.parent.postMessage({ type: "cdd-assistant-close" }, window.location.origin)}><X /></Button>
    </header>
    {loading ? <div className="p-5"><Shimmer>Loading…</Shimmer></div> : state ? <ChatWindow key={state.userId} userId={state.userId} initialMessages={state.messages} /> : <div className="flex flex-1 flex-col items-center justify-center gap-5 p-6 text-center"><img className="size-16" src="/site/assets/images/crop-assistant.svg" alt=""/><p className="text-sm">{notice}</p><Button asChild><a href="/site/pages/login.html" target="_top">Sign in</a></Button></div>}
  </div>;
}

function ChatWindow({ userId, initialMessages }: { userId: string; initialMessages: UIMessage[] }) {
  const [text, setText] = useState("");
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [transport] = useState(() => new DefaultChatTransport({ api: "/api/assistant", headers: async () => {
    const { data } = await supabase.auth.getSession();
    return data.session ? { Authorization: `Bearer ${data.session.access_token}` } : {};
  } }));
  const { messages, sendMessage, status, stop, error, clearError } = useChat({ id: userId, messages: initialMessages, transport });
  const busy = status === "submitted" || status === "streaming";
  useEffect(() => { if (!busy) textarea.current?.focus(); }, [busy]);
  function send(value: string) {
    if (!value.trim() || busy) return;
    clearError();
    void sendMessage({ text: value.trim() });
    setText("");
    textarea.current?.focus();
  }
  return <>
    <Conversation className="min-h-0 flex-1"><ConversationContent className="gap-5 p-4">
      {messages.length === 0 && <div className="py-6"><img src="/site/assets/images/crop-assistant.svg" alt="" className="mb-4 size-14"/><h2 className="mb-5 text-xl font-semibold">Hello! Habari!</h2><div className="flex flex-col items-start gap-2">{["How do I scan my crop?", "My maize leaves are turning yellow", "Ninawezaje kupakia picha?"].map(question => <Button key={question} variant="outline" className="h-auto max-w-full whitespace-normal text-left" onClick={() => send(question)}>{question}</Button>)}</div></div>}
      {messages.map(message => <Message key={message.id} from={message.role}><MessageContent className={message.role === "user" ? "user-message" : ""}>{message.parts.map((part, index) => part.type === "text" ? <MessageResponse key={index} components={{ a: ({ children, ...props }) => <a {...props} target="_top" rel="noopener noreferrer">{children}</a> }}>{part.text}</MessageResponse> : part.type === "reasoning" ? <details key={index} className="text-xs text-muted-foreground"><summary>Thinking</summary><MessageResponse>{part.text}</MessageResponse></details> : null)}</MessageContent></Message>)}
      {status === "submitted" && <Shimmer>Thinking…</Shimmer>}
    </ConversationContent><ConversationScrollButton /></Conversation>
    <div className="shrink-0 border-t border-border p-3">
      {error && <p role="alert" className="mb-2 text-sm text-destructive">{error.message}</p>}
      <PromptInput onSubmit={({ text: submitted }) => send(submitted)}><PromptInputTextarea ref={textarea} value={text} onChange={event => setText(event.target.value)} placeholder="Ask about your crops…" aria-label="Message Crop Assistant" maxLength={8000} className="min-h-16"/><PromptInputFooter className="justify-end"><PromptInputSubmit status={status} onStop={() => { void stop(); }} disabled={!busy && !text.trim()} /></PromptInputFooter></PromptInput>
      <p className="mt-2 text-center text-[11px] text-muted-foreground">General guidance · Not a confirmed crop diagnosis</p>
    </div>
  </>;
}