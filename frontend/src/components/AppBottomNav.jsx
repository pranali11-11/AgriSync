import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BottomNav } from "./BottomNav";

export function AppBottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;
  const activeTab =
    path.startsWith("/plan") || path.startsWith("/map")
      ? "machinery"
      : path.startsWith("/groups")
        ? "community"
        : path.startsWith("/profile")
          ? "profile"
          : path.startsWith("/schemes")
            ? "schemes"
            : path.startsWith("/advisory")
              ? "advisory"
              : "home";

  const routes = {
    home: "/dashboard",
    advisory: "/advisory",
    machinery: "/plan",
    schemes: "/schemes",
    community: "/groups/nearby",
    profile: "/profile",
  };

  return (
    <BottomNav
      activeTab={activeTab}
      onSelectTab={(tab) => navigate(routes[tab])}
    />
  );
}
