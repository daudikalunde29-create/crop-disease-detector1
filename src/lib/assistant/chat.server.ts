import { createClient } from "@supabase/supabase-js";
import { convertToModelMessages, validateUIMessages, type UIMessage } from "ai";
import { z } from "zod";
import type { Database, Json } from "@/integrations/supabase/types";
import { createResponsesCall } from "./responses.server";
import { withLovableAiGatewayRunIdHeader } from "./run-id.ts";
import { ASSISTANT_INSTRUCTIONS } from "./policy";

export async function handleAssistantChat(request: Request) {
  const token = request.headers.get("Authorization")?.match(/^Bearer (.+)$/i)?.[1];
  if (!token) return new Response("Please sign in to chat.", { status: 401 });
  const url = process.env['SUPABASE_URL'];
  const key = process.env['SUPABASE_PUBLISHABLE_KEY'];
  const aiKey = process.env['LOVABLE_API_KEY'];
  if (!url || !key || !aiKey) return new Response("The assistant connection is not configured.", { status: 503 });
  const client = createClient<Database>(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${token}` }, fetch: (input, init) => {
      const headers = new Headers(init?.headers);
      headers.set("apikey", key);
      return fetch(input, { ...init, headers });
    } },
  });
  const { data: auth, error: authError } = await client.auth.getUser(token);
  if (authError || !auth.user) return new Response("Please sign in again to chat.", { status: 401 });
  try {
    const body = z.object({ messages: z.array(z.unknown()).min(1), id: z.string().optional(), trigger: z.string().optional(), messageId: z.string().optional() }).parse(await request.json());
    if (JSON.stringify(body.messages).length > 500000) return new Response("This conversation is too long to send.", { status: 400 });
    const messages = await validateUIMessages<UIMessage>({ messages: body.messages });
    if (messages.some(m => m.role === "system")) return new Response("Invalid message role.", { status: 400 });
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: blocked, error: blockError } = await supabaseAdmin.from("assistant_access_state").select("reason,status").eq("id", "gateway").maybeSingle();
    if (blockError) throw new Error("Assistant availability could not be checked.");
    if (blocked) return new Response(blocked.reason, { status: blocked.status });
    const save = async (next: UIMessage[]) => {
      const { error } = await client.from("assistant_conversations").upsert({ user_id: auth.user.id, messages: next as unknown as Json, updated_at: new Date().toISOString() });
      if (error) throw new Error("Your message could not be saved. Please try again.");
    };
    await save(messages);
    // The helper constructs a request-local provider. Inspect safe gateway errors
    // before sending stream headers and durably pause access-denied requests.
    const call = createResponsesCall(request, { baseURL: "https://ai.gateway.lovable.dev/v1", apiKey: aiKey, model: "openai/gpt-6-astra" }, await convertToModelMessages(messages), ASSISTANT_INSTRUCTIONS);
    const stream = call.result.toUIMessageStreamResponse({
      originalMessages: messages, sendReasoning: true,
      onFinish: async ({ messages: completed }) => { await save(completed); },
      onError: (error) => error instanceof Error ? error.message : "The assistant could not reply. Please try again.",
    });
    return await withLovableAiGatewayRunIdHeader(stream, call.gateway);
  } catch (error) {
    if (request.signal.aborted) return new Response(null, { status: 499 });
    if (error instanceof z.ZodError) return new Response("Invalid chat message.", { status: 400 });
    return new Response(error instanceof Error ? error.message : "The assistant could not reply.", { status: 500 });
  }
}