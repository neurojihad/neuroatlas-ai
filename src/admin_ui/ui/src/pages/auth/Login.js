import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../../shared/hooks/useAuth";
import AuthLayout from "./AuthLayout";

function Login() {
  const location = useLocation();
  const { user, loading, error, redirectToSSOAuthUrl, defaultUserResource } = useAuth();

  const handleSSO = async (event) => {
    event.preventDefault();
    if (!loading) {
      await redirectToSSOAuthUrl(location?.state?.lastPage);
    }
  };

  if (user) {
    return <Navigate to={defaultUserResource()} replace />;
  }

  if (loading) {
    return (
      <AuthLayout>
        <div className="page-center">
          <p className="muted">Checking session…</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className="login-card hud-corners">
        <div className="login-logo">
          <div className="logo-mark">NA</div>
          <div>
            <div className="login-title">NEURAL COMMAND ACCESS</div>
            <div className="login-sub">Pediatric neurorehabilitation CDS</div>
          </div>
        </div>
        <div className="login-divider" />
        <p className="muted" style={{ marginBottom: "1.5rem" }}>
          Secure clinical interface for authorized personnel. Authenticate via organization SSO.
        </p>
        {error ? <p className="error-banner">{error}</p> : null}
        <button type="button" className="btn-primary" disabled={loading} onClick={handleSSO}>
          {loading ? "Redirecting to SSO…" : "▶ INITIATE SSO SESSION"}
        </button>
        <p className="login-footer">Secured via Keycloak · v0.1.0 Pioneer</p>
      </div>
    </AuthLayout>
  );
}

export default Login;
