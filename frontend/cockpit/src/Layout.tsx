import type { ReactNode } from "react";
import {
  Layout as RALayout,
  CheckForApplicationUpdate,
  Menu,
  useResourceDefinitions,
} from "react-admin";
import BookIcon from "@mui/icons-material/Book";

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

export const Layout = ({ children }: { children: ReactNode }) => (
  <RALayout menu={CustomMenu}>
    {children}
    <CheckForApplicationUpdate />
  </RALayout>
);
