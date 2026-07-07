export class ApiConfig {
  static instance;

  storage;

  checkDevMode() {
    if (process.env.NODE_ENV === "development" && !process.env.REACT_APP_ADMIN_URL) {
      console.info("Dev proxy targets http://localhost:8000 (override with REACT_APP_ADMIN_URL).");
    }
  }

  init() {
    this.checkDevMode();

    const adminUrl = "/api/v1";
    const adminUrlGuard = "/guard/api/v1";

    this.storage = {
      api: {
        adminUrlGuard,
      },
      auth: {
        ssoAuthUri: `${adminUrl}/auth`,
        ssoAuthTokenUri: `${adminUrl}/token`,
        ssoAuthMe: `${adminUrl}/auth/me`,
        ssoLogoutUri: `${adminUrl}/logout`,
        ssoAuthRefreshTokenUri: `${adminUrl}/token/refresh`,
      },
    };
  }

  constructor() {
    if (ApiConfig.instance) {
      return ApiConfig.instance;
    }

    this.init();
    ApiConfig.instance = this;
    return this;
  }

  get(key) {
    return key.split(".").reduce((currObject, keyPart) => currObject?.[keyPart], this.storage);
  }
}

export const apiConfig = new ApiConfig();
