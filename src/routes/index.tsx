import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";

// The Crop Disease Detector UI is the static site in public/site.
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Crop Disease Detector — Scan your crops" },
      { name: "description", content: "Upload or capture crop leaf photos and track your scans. Built for farmers in English and Kiswahili." },
      { property: "og:title", content: "Crop Disease Detector" },
      { property: "og:description", content: "Upload or capture crop leaf photos and track your scans." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { httpEquiv: "refresh", content: "0; url=/site/index.html" },
    ],
  }),
  component: Index,
});

function Index() {
  useEffect(() => {
    window.location.replace("/site/index.html");
  }, []);
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <a href="/site/index.html">Opening Crop Disease Detector…</a>
    </div>
  );
}
