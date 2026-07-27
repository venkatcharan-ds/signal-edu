// /signup redirects to /login — GitHub OAuth is the only auth method.
import { redirect } from "next/navigation";

export default function SignupPage() {
  redirect("/login");
}
