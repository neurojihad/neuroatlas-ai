import { hasAnyRole } from "../constants/roles";
import { findRouteInMenu } from "../constants/menu";
import { useAuth } from "../hooks/useAuth";
import { NavigateToAuth } from "./NavigateToAuth";

export const ProtectedRoute = ({ element: Element, path, notFoundElement }) => {
  const { user } = useAuth();

  if (!user) {
    return <NavigateToAuth />;
  }

  const route = findRouteInMenu(path);
  if (!route || !hasAnyRole(user.roles, route.roles)) {
    return notFoundElement;
  }

  return Element;
};
