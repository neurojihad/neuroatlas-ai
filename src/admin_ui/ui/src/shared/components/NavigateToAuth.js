import { Navigate } from "react-router-dom";

export const NavigateToAuth = ({ authPath = "/auth" }) => (
  <Navigate
    to={authPath}
    state={{
      lastPage: window.btoa(window.location.pathname + window.location.search),
    }}
    replace
  />
);
