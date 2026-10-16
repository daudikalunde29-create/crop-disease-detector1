/*
 * Cloud bridge for the static site in public/site.
 * Bundled to public/site/js/cloud.bundle.js with `bun run build:bridge`.
 * Exposes window.CDDCloud so the vanilla-JS pages share the same
 * authenticated Lovable Cloud client as the rest of the app.
 */
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable/index";

type AppUser = {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: "farmer" | "admin";
  provider: string;
  createdAt: string;
};

class CloudError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

function friendly(err: unknown): CloudError {
  if (err instanceof CloudError) return err;
  const e = err as { message?: string; code?: string; status?: number; name?: string };
  const msg = e?.message || "";
  if (e?.name === "TypeError" || /fetch|network/i.test(msg))
    return new CloudError("NETWORK_ERROR", "Cannot reach the server. Check your internet connection and try again.");
  if (/invalid login credentials/i.test(msg))
    return new CloudError("INVALID_CREDENTIALS", "Incorrect email or password.");
  if (/email not confirmed/i.test(msg))
    return new CloudError("EMAIL_NOT_CONFIRMED", "Please confirm your email first — check your inbox for the confirmation link.");
  if (/already registered|already exists/i.test(msg))
    return new CloudError("EMAIL_EXISTS", "An account with this email already exists. Please log in instead.");
  if (/weak|pwned|compromised/i.test(msg))
    return new CloudError("WEAK_PASSWORD", "This password is too weak or has appeared in a data breach. Please choose another.");
  if (/rate limit/i.test(msg))
    return new CloudError("RATE_LIMITED", "Too many attempts. Please wait a minute and try again.");
  if (/jwt|session/i.test(msg))
    return new CloudError("SESSION_EXPIRED", "Your session has expired. Please log in again.");
  return new CloudError(e?.code || "AUTH_ERROR", msg || "Something went wrong. Please try again.");
}

function pageUrl(page: string) {
  return `${window.location.origin}/site/pages/${page}`;
}

async function loadUser(): Promise<AppUser | null> {
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) return null;
  const u = data.user;
  const [{ data: profile }, { data: roles }] = await Promise.all([
    supabase.from("profiles").select("full_name, phone, email, created_at").eq("id", u.id).maybeSingle(),
    supabase.from("user_roles").select("role").eq("user_id", u.id),
  ]);
  const isAdmin = (roles || []).some((r) => r.role === "admin");
  return {
    id: u.id,
    name: (profile?.full_name || (u.user_metadata?.full_name as string) || "").trim(),
    email: u.email || profile?.email || "",
    phone: profile?.phone || "",
    role: isAdmin ? "admin" : "farmer",
    provider: (u.app_metadata?.provider as string) || "email",
    createdAt: profile?.created_at || u.created_at,
  };
}

async function wrap<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    throw friendly(err);
  }
}

const api = {
  session: () => wrap(loadUser),

  register: (input: { fullName: string; email: string; phone?: string; password: string }) =>
    wrap(async () => {
      const { data, error } = await supabase.auth.signUp({
        email: input.email,
        password: input.password,
        options: {
          emailRedirectTo: pageUrl("login.html?confirmed=1"),
          data: { full_name: input.fullName, phone: input.phone || "" },
        },
      });
      if (error) throw error;
      // Existing email: Cloud returns a user with no identities.
      if (data.user && (data.user.identities?.length ?? 0) === 0)
        throw new CloudError("EMAIL_EXISTS", "An account with this email already exists. Please log in instead.");
      if (!data.session) return { needsConfirmation: true, user: null };
      return { needsConfirmation: false, user: await loadUser() };
    }),

  login: (email: string, password: string) =>
    wrap(async () => {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      return loadUser();
    }),

  google: () =>
    wrap(async () => {
      const result = await lovable.auth.signInWithOAuth("google", { redirect_uri: pageUrl("login.html") });
      if (result.error) throw result.error;
      if (result.redirected) return { redirected: true, user: null };
      return { redirected: false, user: await loadUser() };
    }),

  logout: () => wrap(async () => { await supabase.auth.signOut(); }),

  requestPasswordReset: (email: string) =>
    wrap(async () => {
      const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: pageUrl("reset-password.html") });
      if (error) throw error;
      return { ok: true };
    }),

  // Called on reset-password.html after the recovery link has signed the user in.
  confirmPasswordReset: (password: string) =>
    wrap(async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session)
        throw new CloudError("RESET_LINK_INVALID", "This reset link is invalid or has expired. Please request a new one.");
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      await supabase.auth.signOut({ scope: "global" });
      return { ok: true };
    }),

  hasRecoverySession: () => wrap(async () => !!(await supabase.auth.getSession()).data.session),

  changePassword: (currentPassword: string, newPassword: string) =>
    wrap(async () => {
      const { data } = await supabase.auth.getUser();
      if (!data.user?.email) throw new CloudError("SESSION_EXPIRED", "Your session has expired. Please log in again.");
      const check = await supabase.auth.signInWithPassword({ email: data.user.email, password: currentPassword });
      if (check.error) throw new CloudError("INVALID_CREDENTIALS", "Your current password is incorrect.");
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      return { ok: true };
    }),

  updateProfile: (fullName: string, phone: string) =>
    wrap(async () => {
      const { data } = await supabase.auth.getUser();
      if (!data.user) throw new CloudError("SESSION_EXPIRED", "Your session has expired. Please log in again.");
      const { error } = await supabase.from("profiles").update({ full_name: fullName, phone }).eq("id", data.user.id);
      if (error) throw new CloudError("VALIDATION_ERROR", error.message);
      return loadUser();
    }),

  maxFileSize: MAX_FILE_SIZE,
  allowedTypes: ALLOWED_TYPES,

  // Stores the image and an honest "not_ready" scan record. No prediction is generated.
  uploadScan: (file: File) =>
    wrap(async () => {
      if (!ALLOWED_TYPES.includes(file.type)) throw new CloudError("BAD_TYPE", "Please use a JPG, PNG or WEBP image.");
      if (file.size === 0 || file.size > MAX_FILE_SIZE) throw new CloudError("BAD_SIZE", "Please use an image under 5 MB.");
      const { data } = await supabase.auth.getUser();
      if (!data.user) throw new CloudError("SESSION_EXPIRED", "Your session has expired. Please log in again.");
      const ext = file.type.split("/")[1].replace("jpeg", "jpg");
      const path = `${data.user.id}/${crypto.randomUUID()}.${ext}`;
      const up = await supabase.storage.from("scan-images").upload(path, file, { contentType: file.type });
      if (up.error) throw up.error;
      const ins = await supabase
        .from("scans")
        .insert({ user_id: data.user.id, image_path: path, file_name: file.name.slice(0, 200), file_size: file.size, mime_type: file.type })
        .select("id, created_at, status")
        .single();
      if (ins.error) throw ins.error;
      return { status: "not_ready", scan: ins.data };
    }),

  listScans: () =>
    wrap(async () => {
      const { data: u } = await supabase.auth.getUser();
      if (!u.user) return [];
      const { data, error } = await supabase
        .from("scans")
        .select("id, file_name, file_size, status, created_at, image_path")
        .eq("user_id", u.user.id)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data || [];
    }),

  scanImageUrl: (path: string) =>
    wrap(async () => {
      const { data, error } = await supabase.storage.from("scan-images").createSignedUrl(path, 600);
      if (error) throw error;
      return data.signedUrl;
    }),

  deleteScan: (id: string, path: string) =>
    wrap(async () => {
      await supabase.storage.from("scan-images").remove([path]);
      const { error } = await supabase.from("scans").delete().eq("id", id);
      if (error) throw error;
    }),

  // Admin-only: RLS returns other users' rows only to admins.
  adminStats: () =>
    wrap(async () => {
      const [users, scans] = await Promise.all([
        supabase.from("profiles").select("id", { count: "exact", head: true }),
        supabase.from("scans").select("id", { count: "exact", head: true }),
      ]);
      return { users: users.count ?? 0, scans: scans.count ?? 0 };
    }),
};

(window as unknown as { CDDCloud: typeof api }).CDDCloud = api;
window.dispatchEvent(new Event("cdd-cloud-ready"));
