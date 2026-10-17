import { createFileRoute } from "@tanstack/react-router";
import { CropAssistant } from "@/components/crop-assistant";

export const Route = createFileRoute("/assistant")({
  head: () => ({ meta: [
    { title: "Crop Assistant — Crop Disease Detector" },
    { name: "description", content: "Crop care and account help in English and Kiswahili." },
    { property: "og:title", content: "Crop Assistant — Crop Disease Detector" },
    { property: "og:description", content: "Get crop care and account help in English and Kiswahili." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
  ] }),
  component: CropAssistant,
});