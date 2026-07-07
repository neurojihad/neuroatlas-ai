export const CLINICAL_ROLES = ["clinician", "admin"];
export const ALL_APP_ROLES = ["clinician", "admin", "researcher"];

export const hasClinicalAccess = (roles = []) =>
  roles.some((role) => CLINICAL_ROLES.includes(role));

export const hasAnyRole = (roles = [], allowed = []) =>
  roles.some((role) => allowed.includes(role));
