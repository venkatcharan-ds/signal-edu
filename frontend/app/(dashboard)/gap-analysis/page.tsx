import { redirect } from "next/navigation";

// The gap analysis page has moved to /gaps
export default function GapAnalysisRedirect() {
  redirect("/gaps");
}
