<template>
  <section class="workspace-pane variables-pane">
    <VariablesPanel />
  </section>
</template>

<script setup>
defineOptions({ name: "VariablesView" });

import VariablesPanel from "../../components/VariablesPanel.vue";
</script>
