import { usePatientsQuery } from "./queries/patients";

const NeuralMesh = () => (
  <svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="60" r="4" fill="#00e5ff" opacity="0.9" />
    <circle cx="60" cy="30" r="3" fill="#00e5ff" opacity="0.6" />
    <circle cx="140" cy="30" r="3" fill="#ff2bd6" opacity="0.6" />
    <circle cx="40" cy="80" r="3" fill="#39ff88" opacity="0.5" />
    <circle cx="160" cy="80" r="3" fill="#39ff88" opacity="0.5" />
    <circle cx="100" cy="100" r="3" fill="#00e5ff" opacity="0.5" />
    <line x1="100" y1="60" x2="60" y2="30" stroke="#00e5ff" strokeWidth="0.5" opacity="0.4" />
    <line x1="100" y1="60" x2="140" y2="30" stroke="#ff2bd6" strokeWidth="0.5" opacity="0.4" />
    <line x1="100" y1="60" x2="40" y2="80" stroke="#39ff88" strokeWidth="0.5" opacity="0.3" />
    <line x1="100" y1="60" x2="160" y2="80" stroke="#39ff88" strokeWidth="0.5" opacity="0.3" />
    <line x1="100" y1="60" x2="100" y2="100" stroke="#00e5ff" strokeWidth="0.5" opacity="0.3" />
  </svg>
);

function Dashboard() {
  const { data: patients = [] } = usePatientsQuery();

  const recent = [...patients]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  return (
    <>
      <p className="muted" style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", marginBottom: "1.25rem" }}>
        Session active · {new Date().toLocaleString()}
      </p>
      <div className="metrics-row">
        <div className="metric-tile">
          <div className="value">{patients.length}</div>
          <div className="label">Total Patients</div>
        </div>
        <div className="metric-tile">
          <div className="value">—</div>
          <div className="label">Assessments / Week</div>
        </div>
        <div className="metric-tile">
          <div className="value" style={{ color: "var(--warn-amber)" }}>
            —
          </div>
          <div className="label">Pending Predictions</div>
        </div>
        <div className="metric-tile">
          <div className="value" style={{ color: "var(--bio-green)", fontSize: "1.2rem" }}>
            OK
          </div>
          <div className="label">System Health</div>
        </div>
      </div>
      <div className="dash-grid">
        <div className="panel">
          <h3>Recent Activity</h3>
          {recent.length === 0 ? (
            <p className="muted">No patient activity yet.</p>
          ) : (
            recent.map((patient) => (
              <div className="activity-row" key={patient.id}>
                <span>
                  <code>{patient.id}</code> registered
                </span>
                <span className="muted" style={{ fontSize: "0.75rem" }}>
                  {new Date(patient.created_at).toLocaleDateString()}
                </span>
              </div>
            ))
          )}
        </div>
        <div className="panel">
          <h3>Neural Mesh</h3>
          <div className="neural-viz">
            <NeuralMesh />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
