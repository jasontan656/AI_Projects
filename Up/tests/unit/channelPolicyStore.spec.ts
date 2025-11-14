import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useChannelPolicyStore } from "../../src/stores/channelPolicy";

const runCoverageTestsMock = vi.fn();
const validateSecurityMock = vi.fn();

vi.mock("../../src/services/channelPolicyClient", () => ({
  fetchChannelPolicy: vi.fn(),
  saveChannelPolicy: vi.fn(),
  deleteChannelPolicy: vi.fn(),
  fetchChannelHealth: vi.fn(),
  sendChannelTest: vi.fn(),
  runCoverageTests: (...args) => runCoverageTestsMock(...args),
  validateWebhookSecurity: (...args) => validateSecurityMock(...args),
}));

describe("channelPolicy store coverage state", () => {
beforeEach(() => {
  setActivePinia(createPinia());
  runCoverageTestsMock.mockReset();
  validateSecurityMock.mockReset();
});

  it("setCoverage normalizes state", () => {
    const store = useChannelPolicyStore();
    store.setCoverage({
      status: "green",
      updatedAt: "2025-11-13T03:10:00Z",
      scenarios: ["passport_text"],
      mode: "webhook",
      lastError: "",
    });

    expect(store.coverageStatus).toBe("green");
    expect(store.coverageScenarios).toEqual(["passport_text"]);
    expect(store.coverageMode).toBe("webhook");
  });

  it("setCoverage captures polling mode", () => {
    const store = useChannelPolicyStore();
    store.setCoverage({
      status: "pending",
      updatedAt: "2025-11-13T03:20:00Z",
      scenarios: [],
      mode: "polling",
    });
    expect(store.coverageMode).toBe("polling");
  });

  it("runCoverageTests updates coverage and calls API", async () => {
    const store = useChannelPolicyStore();
    runCoverageTestsMock.mockResolvedValue({
      status: "pending",
      updatedAt: "2025-11-13T03:15:00Z",
      scenarios: ["passport_text"],
      mode: "webhook",
    });

    await store.runCoverageTests("wf-passport", { scenarios: ["passport_text"] });
    expect(runCoverageTestsMock).toHaveBeenCalledWith("wf-passport", {
      scenarios: ["passport_text"],
    });
    expect(store.coverageStatus).toBe("pending");
  });

  it("validateSecretUniqueness stores snapshot and blocking message", async () => {
    const store = useChannelPolicyStore();
    validateSecurityMock.mockResolvedValue({
      secret: { isUnique: false, conflicts: ["wf-001"] },
      certificate: { status: "available", daysRemaining: 90 },
    });

    await store.validateSecretUniqueness("wf-001", { secret: "NEW_SECRET" });

    expect(validateSecurityMock).toHaveBeenCalledWith("wf-001", {
      secretToken: "NEW_SECRET",
      certificate: "",
      webhookUrl: "",
    });
    expect(store.securitySnapshot?.secret?.isUnique).toBe(false);
    expect(store.securityBlockingMessage).toContain("wf-001");
  });
});
