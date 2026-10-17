import { describe, it, expect } from "vitest";
import { ASSISTANT_INSTRUCTIONS } from "@/lib/assistant/policy";

describe("crop assistant safety", () => {
  it("does not present chat advice as a confirmed scan diagnosis", () => {
    expect(ASSISTANT_INSTRUCTIONS).toContain("disease prediction model is NOT enabled");
    expect(ASSISTANT_INSTRUCTIONS).toContain("Never claim to diagnose a crop");
  });
});