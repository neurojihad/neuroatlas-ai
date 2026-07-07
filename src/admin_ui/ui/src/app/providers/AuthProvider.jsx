import { useEffect, useState } from "react";

import { AuthContext } from "../../shared/hooks/useAuth";
import { authService } from "../../shared/services/AuthService";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(authService.user);
  const [loading, setLoading] = useState(authService.loading);
  const [error, setError] = useState(authService.error);

  useEffect(() => {
    const handleAuthChange = (newUser, newLoading, newError) => {
      setUser(newUser);
      setLoading(newLoading);
      setError(newError);
    };

    authService.addAuthCallback(handleAuthChange);
    authService.loadUser();

    return () => {
      authService.removeAuthCallback(handleAuthChange);
    };
  }, []);

  if (loading) {
    return (
      <div className="page-center">
        <p className="muted">Checking session…</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        loadUser: authService.loadUser.bind(authService),
        redirectToSSOAuthUrl: authService.redirectToSSOAuthUrl.bind(authService),
        verifySession: authService.verifySession.bind(authService),
        logout: authService.logout.bind(authService),
        defaultUserResource: authService.defaultUserResource.bind(authService),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
