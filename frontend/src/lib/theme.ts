// Mirror the Home Assistant theme (the ingress iframe is same-origin with HA).

const VARS = [
  "primary-color",
  "accent-color",
  "primary-text-color",
  "secondary-text-color",
  "disabled-text-color",
  "divider-color",
  "card-background-color",
  "primary-background-color",
  "secondary-background-color",
  "error-color",
  "warning-color",
  "success-color",
  "info-color",
  "ha-card-border-radius",
  "ha-card-box-shadow",
  "state-icon-color",
];

function parentRoot(): HTMLElement | null {
  try {
    if (window.parent && window.parent !== window) return window.parent.document.documentElement;
  } catch {
    /* cross origin */
  }
  return null;
}

function isDark(): boolean {
  try {
    const hass = (window.parent?.document?.querySelector("home-assistant") as any)?.hass;
    if (hass?.themes && typeof hass.themes.darkMode === "boolean") return hass.themes.darkMode;
  } catch {
    /* ignore */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function syncTheme() {
  const root = document.documentElement;
  const parent = parentRoot();
  const dark = isDark();
  root.dataset.theme = dark ? "dark" : "light";
  if (!parent) return;
  const cs = getComputedStyle(parent);
  for (const v of VARS) {
    const value = cs.getPropertyValue(`--${v}`).trim();
    if (value) root.style.setProperty(`--ha-${v}`, value);
    else root.style.removeProperty(`--ha-${v}`);
  }
  const font = cs.getPropertyValue("--ha-font-family-body").trim() || cs.getPropertyValue("--mdc-typography-font-family").trim();
  if (font) root.style.setProperty("--ha-font", font);
}

export function initTheme() {
  syncTheme();
  const parent = parentRoot();
  if (parent) {
    new MutationObserver(() => syncTheme()).observe(parent, { attributes: true, attributeFilter: ["style", "class"] });
  }
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", syncTheme);
  setInterval(syncTheme, 10000);
}
