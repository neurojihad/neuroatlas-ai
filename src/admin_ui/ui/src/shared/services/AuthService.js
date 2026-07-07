import { flatMenuItems } from "../constants/menu";
import { hasAnyRole } from "../constants/roles";
import { httpAuthApi } from "../api/httpAuthApi";
import { httpUserApi } from "../api/httpUserApi";

const TOKEN_ALIAS = "NEUROATLAS_ACCESS_TOKEN";

class AuthService {
  static instance = null;

  constructor() {
    if (!AuthService.instance) {
      this.user = null;
      this.loading = true;
      this.error = null;
      this.authCallbacks = [];
      this.refreshPromise = null;
      AuthService.instance = this;
    }
    return AuthService.instance;
  }

  didLoginPreviously = () => {
    const accessToken = this._getCookie(TOKEN_ALIAS);
    return Boolean(accessToken);
  };

  addAuthCallback(callback) {
    this.authCallbacks.push(callback);
  }

  removeAuthCallback(callback) {
    this.authCallbacks = this.authCallbacks.filter((existing) => existing !== callback);
  }

  _getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return null;
  }

  _triggerAuthCallback() {
    this.authCallbacks.forEach((callback) => callback(this.user, this.loading, this.error));
  }

  _updateState({ user, loading, error }) {
    this.user = user !== undefined ? user : this.user;
    this.loading = loading !== undefined ? loading : this.loading;
    this.error = error !== undefined ? error : this.error;
    this._triggerAuthCallback();
  }

  defaultUserResource() {
    if (!this.user?.roles?.length) {
      return "/dashboard";
    }

    const firstAllowed = flatMenuItems.find((item) => hasAnyRole(this.user.roles, item.roles));
    return firstAllowed ? `/${firstAllowed.name}` : "/session";
  }

  async loadUser() {
    if (!this.didLoginPreviously()) {
      this._updateState({ user: null, loading: false, error: null });
      return;
    }

    this._updateState({ loading: true, error: null });
    try {
      const response = await httpUserApi.getUser();
      const data = await response.json();
      this._updateState({ user: data.data, loading: false, error: null });
    } catch (error) {
      console.error("Failed to load user profile:", error);
      this._updateState({
        user: null,
        loading: false,
        error: error?.explanation ?? "Authentication failed",
      });
    }
  }

  async redirectToSSOAuthUrl(lastPage = null) {
    this._updateState({ loading: true, error: null });
    try {
      const response = await httpAuthApi.getSSOAuthUrl(lastPage);
      const data = await response.json();
      window.location.assign(data.data.auth_url);
    } catch (error) {
      console.error("Failed to start SSO:", error);
      this._updateState({
        loading: false,
        error: error?.explanation ?? "Unable to start sign-in",
      });
    }
  }

  async verifySession() {
    this._updateState({ loading: true, error: null });
    try {
      if (!this.didLoginPreviously()) {
        throw new Error("No session cookie");
      }
      await this.loadUser();
      if (!this.user) {
        throw new Error("Session verification failed");
      }
      this._updateState({ loading: false, error: null });
    } catch (error) {
      console.error("Session verification failed:", error);
      this._updateState({
        user: null,
        loading: false,
        error: "Unable to verify your session",
      });
    }
  }

  async refreshToken() {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = httpAuthApi
      .refreshToken()
      .then((response) => {
        if (!response.ok) {
          throw new Error("Token refresh failed");
        }
      })
      .catch(() =>
        this.logout().finally(() => {
          this._updateState({ error: "Please sign in again" });
        }),
      )
      .finally(() => {
        this.refreshPromise = null;
      });

    return this.refreshPromise;
  }

  async logout() {
    this._updateState({ loading: true });
    try {
      if (this.didLoginPreviously()) {
        const response = await httpAuthApi.logout();
        const payload = await response.json();
        this._updateState({ user: null, loading: false, error: null });
        if (payload?.data?.logout_url) {
          window.location.assign(payload.data.logout_url);
          return;
        }
      }
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      this._updateState({ user: null, loading: false, error: null });
      window.location.assign("/auth");
    }
  }
}

export const authService = new AuthService();
