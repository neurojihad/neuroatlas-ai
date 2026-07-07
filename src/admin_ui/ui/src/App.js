import { lazy } from "react";
import { withErrorBoundary } from "react-error-boundary";
import { Toaster } from "react-hot-toast";
import { Route, Routes } from "react-router-dom";

import { ConfigError } from "./ConfigError";
import { SuspenseLoader } from "./SuspenseLoader";
import { AuthProvider, QueryClientProvider } from "./app/providers";
import AppLayout from "./layout";
import Callback from "./pages/auth/Callback";
import Login from "./pages/auth/Login";
import NotFoundPage from "./pages/notfound/NotFound";
import { ProtectedRedirect } from "./shared/components/ProtectedRedirect";
import { ProtectedRoute } from "./shared/components/ProtectedRoute";
import { withSuspense } from "./shared/hooks/withSuspense";

const Dashboard = lazy(() => import("./pages/dashboard"));
const Patients = lazy(() => import("./pages/patients"));
const Session = lazy(() => import("./pages/session"));

const withErrorBoundaryHOC = (Component) =>
  withErrorBoundary(Component, {
    fallbackRender: ({ error }) => (
      <div className="page-center">
        <div className="login-card hud-corners">
          <h1 className="login-title">Application error</h1>
          <p className="error-banner">{error?.message ?? "Unexpected failure"}</p>
        </div>
      </div>
    ),
  });

const routes = {
  Dashboard: withErrorBoundaryHOC(withSuspense(Dashboard, { fallback: <SuspenseLoader /> })),
  Patients: withErrorBoundaryHOC(withSuspense(Patients, { fallback: <SuspenseLoader /> })),
  Session: withErrorBoundaryHOC(withSuspense(Session, { fallback: <SuspenseLoader /> })),
  NotFoundPage: withErrorBoundaryHOC(withSuspense(NotFoundPage, { fallback: <SuspenseLoader /> })),
};

function App() {
  if (!window._env_) {
    return <ConfigError />;
  }

  return (
    <QueryClientProvider>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<ProtectedRedirect notFoundElement={<routes.NotFoundPage />} />} />
          <Route path="/auth" element={<Login />} />
          <Route path="/auth/callback" element={<Callback />} />
          <Route path="/" element={<AppLayout />}>
            <Route
              path="dashboard"
              element={
                <ProtectedRoute
                  element={<routes.Dashboard />}
                  path="dashboard"
                  notFoundElement={<routes.NotFoundPage />}
                />
              }
            />
            <Route
              path="patients/*"
              element={
                <ProtectedRoute
                  element={<routes.Patients />}
                  path="patients"
                  notFoundElement={<routes.NotFoundPage />}
                />
              }
            />
            <Route
              path="session"
              element={
                <ProtectedRoute
                  element={<routes.Session />}
                  path="session"
                  notFoundElement={<routes.NotFoundPage />}
                />
              }
            />
            <Route path="*" element={<routes.NotFoundPage />} />
          </Route>
        </Routes>
        <Toaster position="top-center" toastOptions={{ duration: 2500 }} />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
