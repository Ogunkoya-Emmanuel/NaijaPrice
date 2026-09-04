import { createRootRoute, createRoute, createRouter, Outlet } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import Layout from "@/components/Layout";
import { CityProvider } from "@/lib/city-context";
import Dashboard from "@/pages/Dashboard";
import SubmitPrice from "@/pages/SubmitPrice";
import Markets from "@/pages/Markets";
import Skeleton from "@/components/Skeleton";

const CommodityDetail = lazy(() => import("@/pages/CommodityDetail"));
const Trends = lazy(() => import("@/pages/Trends"));
const BudgetPlanner = lazy(() => import("@/pages/BudgetPlanner"));
const ModelPerformance = lazy(() => import("@/pages/ModelPerformance"));

function PageFallback() {
  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-7xl mx-auto">
      <Skeleton className="h-96" />
    </div>
  );
}

const rootRoute = createRootRoute({
  component: () => (
    <CityProvider>
      <Layout>
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </Layout>
    </CityProvider>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Dashboard,
});

const commodityRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/commodity/$id",
  component: CommodityDetail,
});

const submitRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/submit",
  component: SubmitPrice,
});

const marketsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/markets",
  component: Markets,
});

const trendsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/trends",
  component: Trends,
});

const budgetRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/budget",
  component: BudgetPlanner,
});

const modelPerformanceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/model-performance",
  component: ModelPerformance,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  commodityRoute,
  submitRoute,
  marketsRoute,
  trendsRoute,
  budgetRoute,
  modelPerformanceRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
