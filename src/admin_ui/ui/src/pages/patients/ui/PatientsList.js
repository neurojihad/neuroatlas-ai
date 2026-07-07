import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { usePatientsQuery } from "./queries/patients";

const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

function PatientsList() {
  const navigate = useNavigate();
  const { data: patients = [], isLoading, error } = usePatientsQuery();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return patients;
    }
    return patients.filter(
      (patient) =>
        patient.id.toLowerCase().includes(needle) ||
        (patient.diagnosis_code ?? "").toLowerCase().includes(needle),
    );
  }, [patients, query]);

  return (
    <>
      <div className="toolbar">
        <input
          className="search-input"
          type="search"
          placeholder="Search by ID or diagnosis code..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <span className="filter-chip active">All</span>
        <button type="button" className="btn-ghost" style={{ marginLeft: "auto" }} disabled>
          + Register
        </button>
      </div>

      {isLoading ? <p className="muted">Loading patients…</p> : null}
      {error ? <p className="error-banner">{error.explanation ?? "Failed to load patients."}</p> : null}

      {!isLoading && !error && filtered.length === 0 ? (
        <div className="empty-state">
          <p>No neural profiles indexed yet.</p>
        </div>
      ) : null}

      {!isLoading && !error && filtered.length > 0 ? (
        <div className="panel table-wrap" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Year of Birth</th>
                <th>Sex</th>
                <th>Diagnosis</th>
                <th>Registered</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((patient) => (
                <tr
                  key={patient.id}
                  className="row-link"
                  onClick={() => navigate(`/patients/${patient.id}`)}
                >
                  <td>
                    <code>{patient.id}</code>
                  </td>
                  <td>{patient.date_of_birth_year}</td>
                  <td>{patient.sex ?? "—"}</td>
                  <td>{patient.diagnosis_code ?? "—"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {formatDate(patient.created_at)}
                  </td>
                  <td>
                    <span className="status-dot green" />
                    Active
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}

export default PatientsList;
