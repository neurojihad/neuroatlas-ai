export const menuItems = [
  {
    name: "dashboard",
    label: "Command Center",
    roles: ["clinician", "admin"],
  },
  {
    name: "patients",
    label: "Patients Registry",
    roles: ["clinician", "admin"],
  },
  {
    name: "session",
    label: "Session Matrix",
    roles: ["clinician", "admin", "researcher"],
  },
];

export const flatMenuItems = menuItems;

export const findRouteInMenu = (path) =>
  flatMenuItems.find((item) => item.name === path) ?? null;
