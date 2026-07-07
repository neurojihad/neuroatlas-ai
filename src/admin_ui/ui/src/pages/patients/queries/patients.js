import { useQuery } from "@tanstack/react-query";

import { httpPatientsApi } from "../../../shared/api/httpPatientsApi";

export const patientsKeys = {
  all: ["patients"],
  list: () => [...patientsKeys.all, "list"],
  detail: (id) => [...patientsKeys.all, "detail", id],
};

export const fetchPatients = async () => {
  const response = await httpPatientsApi.listPatients();
  const payload = await response.json();
  return payload.data;
};

export const fetchPatient = async (patientId) => {
  const response = await httpPatientsApi.getPatient(patientId);
  const payload = await response.json();
  return payload.data;
};

export const usePatientsQuery = () =>
  useQuery({
    queryKey: patientsKeys.list(),
    queryFn: fetchPatients,
  });

export const usePatientQuery = (patientId) =>
  useQuery({
    queryKey: patientsKeys.detail(patientId),
    queryFn: () => fetchPatient(patientId),
    enabled: Boolean(patientId),
  });
