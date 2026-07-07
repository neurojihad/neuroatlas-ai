import { ERROR_CASES, HTTP, NETWORK } from "../constants/api";
import { authService } from "../services/AuthService";
import { generateUID } from "../utils/generate";
import HttpBase from "./HttpBase";

const httpError = ({ status, details, ...config }) => {
  const explanation = ERROR_CASES[status] ?? "Request failed";
  return {
    status,
    ...config,
    showToast: true,
    errorType: HTTP,
    explanation: details ? `${explanation}: ${details}` : explanation,
  };
};

const networkError = (config) => ({
  showToast: true,
  ...config,
  errorType: NETWORK,
  explanation: "Network request failed",
});

class HttpAuthBase extends HttpBase {
  async request(url, options = {}) {
    const fullUrl = (this.baseOptions.baseURL || "") + url;
    const isFormData = options?.body instanceof FormData;

    const mergedOptions = {
      ...this.baseOptions,
      ...options,
      headers: {
        ...(isFormData ? {} : this.defaultHeaders),
        ...this.baseOptions.headers,
        ...(options?.headers || {}),
      },
    };

    const correlationId = generateUID("crr");
    mergedOptions.headers["X-Correlation-Id"] = correlationId;

    let response = await fetch(fullUrl, mergedOptions).catch((error) => {
      throw networkError({
        reason: error?.message ?? null,
        cause: error,
        showToast: error?.name !== "AbortError",
        errorName: error?.name,
      });
    });

    if (response.status === 401) {
      await authService.refreshToken();
      if (authService.user) {
        response = await fetch(fullUrl, mergedOptions);
      }
    }

    if (!response.ok) {
      const errorResponse = (await response.json().catch(() => null)) ?? null;
      const details = errorResponse?.details ?? errorResponse?.message ?? null;
      throw httpError({
        status: response.status,
        statusText: response.statusText,
        correlationId,
        details,
      });
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

export default HttpAuthBase;
