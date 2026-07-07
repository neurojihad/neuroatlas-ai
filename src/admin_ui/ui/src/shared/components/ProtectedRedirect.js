import { Navigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { NavigateToAuth } from "./NavigateToAuth";

export const ProtectedRedirect = ({ notFoundElement = null }) => {
  const { user, defaultUserResource } = useAuth();

  if (!user) {
    return <NavigateToAuth />;
  }

  return <Navigate to={defaultUserResource()} replace />;
};
