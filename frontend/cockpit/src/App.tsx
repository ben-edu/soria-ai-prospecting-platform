import { Admin, Resource } from "react-admin";
import { dataProvider } from "./dataProvider";
import { Layout } from "./Layout";
import {
  CompanyList,
  CompanyCreate,
  CompanyEdit,
  CompanyShow,
} from "./resources/companies";

export const App = () => (
  <Admin
    dataProvider={dataProvider}
    layout={Layout}
    title="SORIA Prospecting Cockpit"
  >
    <Resource
      name="companies"
      list={CompanyList}
      create={CompanyCreate}
      edit={CompanyEdit}
      show={CompanyShow}
    />
  </Admin>
);
