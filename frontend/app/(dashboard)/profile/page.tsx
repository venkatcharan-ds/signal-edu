import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { ProfileView } from "./ProfileView";

export const metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <>
      <Header pageTitle="Profile" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-4xl w-full mx-auto">
        <PageEnter>
          <ProfileView />
        </PageEnter>
      </main>
    </>
  );
}
