import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import "./styles.css";
import { connect } from "./lib/store";
import { initTheme } from "./lib/theme";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", component: () => import("./views/Overview.vue") },
    { path: "/devices", component: () => import("./views/Devices.vue") },
    { path: "/groups", component: () => import("./views/Groups.vue") },
    { path: "/sensors", component: () => import("./views/Sensors.vue") },
    { path: "/direct", component: () => import("./views/DirectControl.vue") },
    { path: "/automations", component: () => import("./views/Automations.vue") },
    { path: "/bus", component: () => import("./views/Bus.vue") },
    { path: "/analytics", component: () => import("./views/Analytics.vue") },
    { path: "/system", component: () => import("./views/System.vue") },
    { path: "/expert", component: () => import("./views/Expert.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

// After an add-on update an open tab still references old chunk names → reload once.
router.onError((err, to) => {
  const msg = String((err as Error)?.message || err);
  if (!/dynamically imported module|Importing a module script failed|Unable to preload CSS/i.test(msg)) return;
  try {
    const last = Number(sessionStorage.getItem("lunatone.reloaded") || 0);
    if (Date.now() - last < 10000) return; // avoid reload loops
    sessionStorage.setItem("lunatone.reloaded", String(Date.now()));
  } catch {
    /* ignore */
  }
  window.location.hash = to.fullPath;
  window.location.reload();
});

initTheme();
connect();
createApp(App).use(router).mount("#app");
