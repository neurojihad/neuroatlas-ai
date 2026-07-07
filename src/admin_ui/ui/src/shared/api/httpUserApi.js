import { apiConfig } from "../config";
import HttpAuthBase from "./HttpAuthBase";

class HttpUserApi extends HttpAuthBase {
  async getUser() {
    return this.get(apiConfig.get("auth.ssoAuthMe"));
  }
}

export const httpUserApi = new HttpUserApi();
