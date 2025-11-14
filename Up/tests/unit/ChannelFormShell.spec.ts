import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import ChannelFormShell from "@up/components/channel-form/ChannelFormShell.vue";

describe("ChannelFormShell", () => {
  it("renders slots when published", () => {
    const wrapper = mount(ChannelFormShell, {
      props: {
        published: true,
        title: "Demo",
      },
      slots: {
        default: "<div class='body-slot'>Inner</div>",
        actions: "<button>Save</button>",
      },
    });

    expect(wrapper.find(".body-slot").exists()).toBe(true);
    expect(wrapper.text()).toContain("Demo");
  });

  it("shows placeholder and emits go-publish", async () => {
    const wrapper = mount(ChannelFormShell, {
      props: {
        published: false,
      },
    });

    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted()["go-publish"]).toHaveLength(1);
  });
});
