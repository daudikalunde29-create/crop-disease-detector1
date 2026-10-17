import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export const getAssistantHistory = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { data, error } = await context.supabase.from("assistant_conversations")
      .select("messages").eq("user_id", context.userId).maybeSingle();
    if (error) throw new Error("Your conversation could not be loaded. Please try again.");
    return data?.messages ?? [];
  });