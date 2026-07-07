import { generateUID } from "../utils/generate";

class HttpBase {
  constructor(baseOptions = {}) {
    this.baseOptions = {
      credentials: "include",
      ...baseOptions,
    };
    this.defaultHeaders = {
      "Content-Type": "application/json",
      "X-Correlation-Id": generateUID("crr"),
    };
  }

  async request(url, options = {}) {
    const fullUrl = (this.baseOptions.baseURL || "") + url;
    const isFormData = options.body instanceof FormData;

    const mergedOptions = {
      ...this.baseOptions,
      ...options,
      headers: {
        ...(isFormData ? {} : this.defaultHeaders),
        ...this.baseOptions.headers,
        ...(options.headers || {}),
      },
    };

    const response = await fetch(fullUrl, mergedOptions);

    if (!response.ok) {
      const respJson = (await response.json().catch(() => null)) ?? null;
      throw {
        status: response.status,
        statusText: response.statusText,
        response: respJson?.details ?? respJson?.message ?? "",
      };
    }

    return response;
  }

  async get(url, options) {
    return this.request(url, { ...options, method: "GET" });
  }

  async post(url, data, options) {
    const isFormData = data instanceof FormData;
    return this.request(url, {
      ...options,
      method: "POST",
      body: isFormData ? data : data !== undefined ? JSON.stringify(data) : undefined,
    });
  }
}

export default HttpBase;
