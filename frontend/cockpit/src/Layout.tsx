import type { ReactNode } from "react";
import {
  AppBar,
  CheckForApplicationUpdate,
  Layout as RALayout,
  Menu,
  TitlePortal,
} from "react-admin";
import BookIcon from "@mui/icons-material/Book";
import LogoutIcon from "@mui/icons-material/Logout";
import SearchIcon from "@mui/icons-material/Search";
import WorkIcon from "@mui/icons-material/Work";
import MailOutlineIcon from "@mui/icons-material/MailOutline";
import ScheduleIcon from "@mui/icons-material/Schedule";
import { Box, IconButton, Tooltip } from "@mui/material";

const CustomMenu = () => (
  <Menu>
    <Menu.Item
      to="/external-sources"
      primaryText="External Search"
      leftIcon={<SearchIcon />}
    />
    <Menu.Item
      to="/opportunities"
      primaryText="Opportunities"
      leftIcon={<WorkIcon />}
    />
    <Menu.Item
      to="/message-drafts"
      primaryText="Message Drafts"
      leftIcon={<MailOutlineIcon />}
    />
    <Menu.Item
      to="/follow-ups"
      primaryText="Follow-ups"
      leftIcon={<ScheduleIcon />}
    />
    <Menu.Item
      to="/source-catalog"
      primaryText="Source Catalog"
      leftIcon={<BookIcon />}
    />
  </Menu>
);

const CustomAppBar = () => {
  const handleLogout = () => {
    const postLogoutRedirectUri = `${window.location.origin}/`;
    const keycloakLogoutUrl =
      "https://keycloak.soria-academie.fr/realms/soria/protocol/openid-connect/logout" +
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
