import { createContext, useContext } from "react";

export const AuthContext = createContext(null);

export const useAuth = () => {
  const authContext = useContext(AuthContext);

  if (!authContext) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return authContext;
};
