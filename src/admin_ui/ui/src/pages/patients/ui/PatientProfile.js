import { useParams } from "react-router-dom";

import { usePatientQuery } from "../queries/patients";

function PatientProfile() {
  const { patientId } = useParams();
  const { data: patient, isLoading, error } = usePatientQuery(patientId);

  if (isLoading) {
    return <p className="muted">Loading neural profile…</p>;
  }

  if (error || !patient) {
    return <p className="error-banner">{error?.explanation ?? "Patient not found."}</p>;
  }

  return (
    <>
      <div className="profile-hero">
        <div className="profile-id">{patient.id}</div>
        <div className="profile-meta">
          Born {patient.date_of_birth_year} · {patient.sex ?? "—"} · Diagnosis{" "}
          {patient.diagnosis_code ?? "—"}
        </div>
      </div>
      <div className="tab-strip">
        <div className="tab active">Overview</div>
        <div className="tab">Assessments</div>
        <div className="tab locked">Predictions (Phase 2)</div>
      </div>
      <div className="panel">
        <h3>Clinical Summary</h3>
        <p className="muted" style={{ marginBottom: "0.75rem" }}>
          Registered {new Date(patient.created_at).toLocaleDateString()} · Assessments coming in Phase
          2 · No ML predictions yet
        </p>
        <div className="sparkline" aria-hidden="true" />
        <p className="muted" style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem" }}>
          Recovery trajectory placeholder — live data in Phase 2
        </p>
      </div>
    </>
  );
}

export default PatientProfile;
