import { Suspense } from "react";

export const withSuspense = (Component, { fallback = null } = {}) => {
  const Wrapped = (props) => (
    <Suspense fallback={fallback}>
      <Component {...props} />
    </Suspense>
  );
  Wrapped.displayName = `withSuspense(${Component.displayName || Component.name || "Component"})`;
  return Wrapped;
};
