import { ProjectsView } from "./ProjectsView";

export const metadata = {
  title: "Projects — SIGNAL",
};

export default function ProjectsPage() {
  return (
    <main className="flex-1 px-6 py-8 max-w-5xl mx-auto w-full">
      <ProjectsView />
    </main>
  );
}
