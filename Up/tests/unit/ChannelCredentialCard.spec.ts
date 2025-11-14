import { describe, expect, it } from "vitest";
import { createRequire } from "module";
import { reactive } from "vue";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import ChannelCredentialCard from "@up/components/channel-form/ChannelCredentialCard.vue";

describe("ChannelCredentialCard", () => {
  const createForm = () =>
    reactive({
      botToken: "",
      maskedBotToken: "1234567890",
      webhookUrl: "https://demo.example",
      usePolling: false,
      waitForResult: true,
      workflowMissingMessage: "",
      timeoutMessage: "",
    });

  it("emits enable-token-edit when edit button clicked", async () => {
    const wrapper = mount(ChannelCredentialCard, {
      props: {
        form: createForm(),
        errors: {},
        showTokenInput: false,
        hasMaskedToken: true,
        maskedToken: "123***5678",
        pollingMode: false,
        showWebhookWarning: false,
      },
    });

    await wrapper.find('[data-test="credential-token-edit"]').trigger("click");
    expect(wrapper.emitted()["enable-token-edit"]).toBeTruthy();
  });

  it("shows warning when whitelist check fails", () => {
    const wrapper = mount(ChannelCredentialCard, {
      props: {
        form: createForm(),
        errors: {},
        showTokenInput: true,
        hasMaskedToken: false,
        maskedToken: "",
        pollingMode: false,
        showWebhookWarning: true,
      },
    });

    expect(
      wrapper.find(".channel-credential-card__warning").exists(),
    ).toBe(true);
  });

  it("emits toggle when polling switch changes", async () => {
    const wrapper = mount(ChannelCredentialCard, {
      props: {
        form: createForm(),
        errors: {},
        showTokenInput: true,
        hasMaskedToken: false,
        maskedToken: "",
        pollingMode: false,
        showWebhookWarning: false,
      },
    });

    await wrapper
      .find('[data-test="credential-polling-switch"] input')
      .setValue(true);
    expect(wrapper.emitted()["toggle-polling"]).toBeTruthy();
  });
});
