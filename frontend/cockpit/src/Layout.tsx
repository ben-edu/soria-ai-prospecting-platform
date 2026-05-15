import type { ReactNode } from "react";
import {
  AppBar,
  CheckForApplicationUpdate,
  Layout as RALayout,
  Menu,
  TitlePortal,
  useResourceDefinitions,
} from "react-admin";
import BookIcon from "@mui/icons-material/Book";
import LogoutIcon from "@mui/icons-material/Logout";
import { Box, IconButton, Tooltip } from "@mui/material";

const CustomMenu = () => {
  const resources = useResourceDefinitions();

  return (
    <Menu>
      {Object.keys(resources).map((name) => (
        <Menu.ResourceItem key={name} name={name} />
      ))}
      <Menu.Item
        to="/source-catalog"
        primaryText="Source Catalog"
        leftIcon={<BookIcon />}
      />
    </Menu>
  );
};

const CustomAppBar = () => {
  const handleLogout = () => {
    const postLogoutRedirectUri = `${window.location.origin}/`;
    const keycloakLogoutUrl =
      "https://keycloak.behnam.fr/realms/soria/protocol/openid-connect/logout" +
      "?client_id=soria-cockpit" +
      `&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}`;

    const logoutUrl = `/oauth2/sign_out?rd=${encodeURIComponent(
      keycloakLogoutUrl,
    )}`;

    window.location.href = logoutUrl;
  };

  return (
    <AppBar>
      <TitlePortal />
      <Box sx={{ flexGrow: 1 }} />
      <Tooltip title="Logout">
        <IconButton color="inherit" onClick={handleLogout} aria-label="Logout">
          <LogoutIcon />
        </IconButton>
      </Tooltip>
    </AppBar>
  );
};

export const Layout = ({ children }: { children: ReactNode }) => (
  <RALayout menu={CustomMenu} appBar={CustomAppBar}>
    {children}
    <CheckForApplicationUpdate />
  </RALayout>
);
