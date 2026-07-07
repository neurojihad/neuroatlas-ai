import { apiConfig } from "../config";
import HttpBase from "./HttpBase";

class HttpAuthApi extends HttpBase {
  async getSSOAuthUrl(lastPage = null) {
    let redirect = "/dashboard";
    if (lastPage) {
      try {
        redirect = window.atob(lastPage);
      } catch {
        redirect = "/dashboard";
      }
    }
    if (!redirect.startsWith("/") || redirect.startsWith("//")) {
      redirect = "/dashboard";
    }
    const url = `${apiConfig.get("auth.ssoAuthUri")}?redirect=${encodeURIComponent(redirect)}`;
    return this.get(url);
  }

  async logout() {
    return this.post(apiConfig.get("auth.ssoLogoutUri"));
  }

  async refreshToken() {
    return this.post(apiConfig.get("auth.ssoAuthRefreshTokenUri"));
  }
}

export const httpAuthApi = new HttpAuthApi();
