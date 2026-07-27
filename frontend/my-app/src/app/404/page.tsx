import { notFound } from "next/navigation";

/** Explicit route for client-side navigation to the shared 404 UI. */
export default function FourOhFourPage() {
  notFound();
}
