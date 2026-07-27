import { createClient } from "@/lib/supabase-server";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();

  // getUser() validates server-side — never use getSession() in server components
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error || !user) redirect("/login");

  // Supabase stores GitHub identity in user_metadata after GitHub OAuth
  const meta = (user.user_metadata ?? {}) as Record<string, string>;

  const userData = {
    id:       user.id,
    name:     meta.full_name ?? meta.name ?? null,
    email:    user.email ?? null,
    avatar:   meta.avatar_url ?? null,
    username: meta.user_name ?? meta.preferred_username ?? null,
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar user={userData} />
      <div className="flex-1 flex flex-col min-w-0">
        {children}
      </div>
    </div>
  );
}
