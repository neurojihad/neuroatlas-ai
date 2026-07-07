import { Outlet, useLocation } from "react-router-dom";

import { NavigateToAuth } from "../shared/components/NavigateToAuth";
import { flatMenuItems } from "../shared/constants/menu";
import { hasAnyRole } from "../shared/constants/roles";
import { useAuth } from "../shared/hooks/useAuth";
import { BackgroundLayer } from "./BackgroundLayer";
import { Menu } from "./components/Menu";

const titleForPath = (pathname) => {
  const parts = pathname.split("/").filter(Boolean);
  const segment = parts[0] ?? "dashboard";
  if (segment === "patients" && parts.length > 1) {
    return "NEURAL PROFILE";
  }
  const item = flatMenuItems.find((entry) => entry.name === segment);
  return item?.label?.toUpperCase() ?? "NEUROATLAS";
};

const primaryRole = (roles = []) => {
  if (roles.includes("admin")) {
    return "admin";
  }
  if (roles.includes("clinician")) {
    return "clinician";
  }
  return roles[0] ?? "user";
};

export const AppLayout = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  if (!user) {
    return <NavigateToAuth />;
  }

  const segment = location.pathname.split("/").filter(Boolean)[0] ?? "dashboard";
  const route = flatMenuItems.find((item) => item.name === segment);
  if (route && !hasAnyRole(user.roles, route.roles)) {
    return (
      <>
        <BackgroundLayer />
        <div className="page-center">
          <div className="login-card hud-corners">
            <h1 className="login-title">Access denied</h1>
            <p className="muted">Your role cannot access this route.</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <BackgroundLayer />
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-brand">NEUROATLAS</div>
          <Menu />
        </aside>
        <div className="main-area">
          <header className="topbar">
            <span className="topbar-title">{titleForPath(location.pathname)}</span>
            <div className="topbar-user">
              <span className={`role-chip ${primaryRole(user.roles) === "admin" ? "admin" : ""}`}>
                {primaryRole(user.roles)}
              </span>
              <span>{user.email}</span>
              <button type="button" className="btn-ghost" onClick={() => void logout()}>
                Sign out
              </button>
            </div>
          </header>
          <main className="content">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
};

export default AppLayout;
