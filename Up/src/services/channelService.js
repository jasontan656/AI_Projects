import {
  fetchChannelPolicy,
  saveChannelPolicy,
  deleteChannelPolicy,
  fetchChannelHealth,
  sendChannelTest,
} from \"./channelPolicyClient\";

// Deprecated: prefer importing functions from channelPolicyClient directly.
export {
  fetchChannelPolicy as getChannelPolicy,
  saveChannelPolicy,
  deleteChannelPolicy,
  fetchChannelHealth,
  sendChannelTest,
};
