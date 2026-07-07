import { QueryClientProvider as TanStackQueryClientProvider } from "@tanstack/react-query";

import { queryClient } from "../../shared/config";

export const QueryClientProvider = ({ children }) => (
  <TanStackQueryClientProvider client={queryClient}>{children}</TanStackQueryClientProvider>
);
