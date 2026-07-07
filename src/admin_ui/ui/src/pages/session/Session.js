import { flatMenuItems } from "../../shared/constants/menu";
import { useAuth } from "../../shared/hooks/useAuth";
import { authService } from "../../shared/services/AuthService";

function Session() {
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  const matrixRoutes = [
    ...flatMenuItems.map((item) => item.name),
    "ml",
  ];

  return (
    <div className="session-grid">
      <div className="panel identity-card">
        <h3>Identity</h3>
        <div className="email">{user.email}</div>
        <div className="uid">{user.user_id}</div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {user.roles.map((role) => (
            <span key={role} className={`role-chip ${role === "admin" ? "admin" : ""}`}>
              {role}
            </span>
          ))}
        </div>
        <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="button" className="btn-ghost" onClick={() => void authService.loadUser()}>
            Refresh session
          </button>
          <button type="button" className="btn-ghost danger" onClick={() => void logout()}>
            Sign out
          </button>
        </div>
      </div>
      <div className="panel">
        <h3>Access Matrix</h3>
        <table className="data-table access-matrix">
          <thead>
            <tr>
              <th>Route</th>
              <th>clinician</th>
              <th>admin</th>
              <th>researcher</th>
            </tr>
          </thead>
          <tbody>
            {matrixRoutes.map((routeName) => {
              const menuItem = flatMenuItems.find((item) => item.name === routeName);
              const roles = menuItem?.roles ?? (routeName === "ml" ? ["admin"] : []);
              return (
                <tr key={routeName}>
                  <td>/{routeName}</td>
                  <td className={roles.includes("clinician") ? "check" : "cross"}>
                    {roles.includes("clinician") ? "✓" : "—"}
                  </td>
                  <td className={roles.includes("admin") ? "check" : "cross"}>
                    {roles.includes("admin") ? "✓" : "—"}
                  </td>
                  <td className={roles.includes("researcher") ? "check" : "cross"}>
                    {roles.includes("researcher") ? "✓" : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Session;
