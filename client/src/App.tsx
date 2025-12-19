import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppShell from "@/app/AppShell";
import AppRoutes from "@/app/routes";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AppShell>
           <AppRoutes />
        </AppShell>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
