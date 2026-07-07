import { apiConfig } from "../config";
import HttpAuthBase from "./HttpAuthBase";

class HttpPatientsApi extends HttpAuthBase {
  async listPatients() {
    return this.get(`${apiConfig.get("api.adminUrlGuard")}/patients`);
  }

  async getPatient(patientId) {
    return this.get(`${apiConfig.get("api.adminUrlGuard")}/patients/${patientId}`);
  }

  async listAssessments(patientId) {
    return this.get(`${apiConfig.get("api.adminUrlGuard")}/patients/${patientId}/assessments`);
  }
}

export const httpPatientsApi = new HttpPatientsApi();
