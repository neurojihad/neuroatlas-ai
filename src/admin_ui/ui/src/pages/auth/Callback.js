import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../shared/hooks/useAuth";
import AuthLayout from "./AuthLayout";

function Callback() {
  const { user, loading, error, verifySession, defaultUserResource } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const run = async () => {
      if (user) {
        navigate(defaultUserResource(), { replace: true });
        return;
      }
      await verifySession();
    };
    void run();
  }, [user, verifySession, navigate, defaultUserResource]);

  useEffect(() => {
    if (user && !loading) {
      navigate(defaultUserResource(), { replace: true });
    }
  }, [user, loading, navigate, defaultUserResource]);

  return (
    <AuthLayout>
      {error ? (
        <div className="loader-card hud-corners">
          <div className="loader-title">Sign-in failed</div>
          <p className="error-banner">{error}</p>
          <button type="button" className="btn-primary" onClick={() => navigate("/auth")}>
            Back to sign in
          </button>
        </div>
      ) : (
        <div className="loader-card hud-corners">
          <div className="loader-ring" aria-hidden="true" />
          <div className="loader-title">SYNCHRONIZING SESSION</div>
          <p className="muted">Verifying neural link with Keycloak…</p>
          <div className="progress-bar">
            <div className="progress-fill" />
          </div>
        </div>
      )}
    </AuthLayout>
  );
}

export default Callback;
