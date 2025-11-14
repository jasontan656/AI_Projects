import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import ChannelFieldsSecurity from "@up/components/channel-form/ChannelFieldsSecurity.vue";

describe("ChannelFieldsSecurity", () => {
  it("emits secret update when input changes", async () => {
    const wrapper = mount(ChannelFieldsSecurity, {
      props: {
        secret: "",
      },
    });

    const input = wrapper.find('[data-test="security-secret-input"] input');
    await input.setValue("NEw_SECRET");
    expect(wrapper.emitted()["update:secret"][0]).toEqual(["NEw_SECRET"]);
  });

  it("displays conflict warning when secret is not unique", () => {
    const wrapper = mount(ChannelFieldsSecurity, {
      props: {
        secret: "abc",
        validationResult: {
          secret: { isUnique: false, conflicts: ["wf-01", "wf-02"] },
        },
      },
    });

    expect(wrapper.find('[data-test="security-secret-conflict"]').exists()).toBe(
      true,
    );
  });

  it("renders certificate warning when days remaining below threshold", () => {
    const wrapper = mount(ChannelFieldsSecurity, {
      props: {
        secret: "abc",
        validationResult: {
          certificate: { status: "available", daysRemaining: 5 },
        },
      },
    });

    expect(wrapper.find('[data-test="security-cert-warning"]').text()).toContain(
      "5",
    );
  });

  it("emits validate event with current values", async () => {
    const wrapper = mount(ChannelFieldsSecurity, {
      props: {
        secret: "abc123",
      },
    });

    await wrapper
      .find('[data-test="security-validate-btn"]')
      .trigger("click");
    expect(wrapper.emitted().validate[0][0]).toMatchObject({
      secret: "abc123",
    });
  });
});
