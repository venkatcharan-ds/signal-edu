import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { RecommendationsView } from "./RecommendationsView";

export const metadata = { title: "Recommendations" };

export default function RecommendationsPage() {
  return (
    <>
      <Header pageTitle="Recommendations" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-3xl w-full mx-auto">
        <PageEnter>
          <RecommendationsView />
        </PageEnter>
      </main>
    </>
  );
}
