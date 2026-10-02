import React, { Suspense, lazy } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useOnboardingStore } from "./store/useOnboardingStore";
import "./i18n/i18n";

const OnboardingWizard = lazy(() =>
  import("./features/onboarding/OnboardingWizard").then((m) => ({
    default: m.OnboardingWizard,
  })),
);
const AdvisoryPage = lazy(() => import("./features/advisory/AdvisoryPage"));
const HomePage = lazy(() => import("./features/home/HomePage"));
const ResourceMapPage = lazy(
  () => import("./features/resources/ResourceMapPage"),
);
const MachineryPlanPage = lazy(
  () => import("./features/machineryPlan/MachineryPlanPage"),
);
const ProfilePage = lazy(() => import("./features/profile/ProfilePage"));
const NearbyGroups = lazy(() =>
  import("./features/groups/GroupPages").then((module) => ({
    default: module.NearbyGroups,
  })),
);
const GroupDetailPage = lazy(() =>
  import("./features/groups/GroupPages").then((module) => ({
    default: module.GroupDetailPage,
  })),
);
const MineGroups = lazy(() =>
  import("./features/groups/GroupPages").then((module) => ({
    default: module.MineGroups,
  })),
);
const NewGroup = lazy(() =>
  import("./features/groups/GroupPages").then((module) => ({
    default: module.NewGroup,
  })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

function AppRoutes() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token, step } = useOnboardingStore();
  const onboardingDone = token && step >= 7;

  const handleOnboardingComplete = () => {
    navigate("/dashboard", { replace: true });
  };

  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-agri-green-700 flex items-center justify-center animate-pulse">
              <span className="text-2xl">🌱</span>
            </div>
            <p className="text-slate-400 text-sm font-semibold animate-pulse">
              Loading AgriSync…
            </p>
          </div>
        </div>
      }
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18 }}
        >
          <Routes location={location}>
            <Route
              path="/"
              element={
                onboardingDone ? (
                  <Navigate to="/dashboard" replace />
                ) : (
                  <OnboardingWizard onComplete={handleOnboardingComplete} />
                )
              }
            />
            <Route
              path="/onboarding"
              element={
                <OnboardingWizard onComplete={handleOnboardingComplete} />
              }
            />
            <Route
              path="/dashboard"
              element={token ? <HomePage /> : <Navigate to="/" replace />}
            />
            <Route
              path="/advisory"
              element={token ? <AdvisoryPage /> : <Navigate to="/" replace />}
            />
            <Route
              path="/map"
              element={
                token ? <ResourceMapPage /> : <Navigate to="/" replace />
              }
            />
            <Route
              path="/plan"
              element={
                token ? <MachineryPlanPage /> : <Navigate to="/" replace />
              }
            />
            <Route
              path="/profile"
              element={token ? <ProfilePage /> : <Navigate to="/" replace />}
            />
            <Route
              path="/booking"
              element={
                token ? (
                  <div className="p-8 font-bold">Booking is coming soon.</div>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/booking/group"
              element={
                token ? (
                  <div className="p-8 font-bold">
                    Group booking is coming soon.
                  </div>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/groups/nearby"
              element={token ? <NearbyGroups /> : <Navigate to="/" replace />}
            />
            <Route
              path="/groups/new"
              element={token ? <NewGroup /> : <Navigate to="/" replace />}
            />
            <Route
              path="/groups/mine"
              element={token ? <MineGroups /> : <Navigate to="/" replace />}
            />
            <Route
              path="/groups/:id"
              element={
                token ? <GroupDetailPage /> : <Navigate to="/" replace />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </motion.div>
      </AnimatePresence>
    </Suspense>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 3500,
            style: {
              background: "#1e293b",
              color: "#f1f5f9",
              border: "1px solid #334155",
              borderRadius: "16px",
              fontWeight: 600,
              fontSize: "14px",
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
