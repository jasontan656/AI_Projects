import { createRouter, createWebHistory } from "vue-router";

import PipelineWorkspace from "../views/PipelineWorkspace.vue";

const routes = [
  {
    path: "/pipelines",
    name: "PipelineWorkspace",
    component: PipelineWorkspace,
  },
  {
    path: "/",
    redirect: "/pipelines",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
