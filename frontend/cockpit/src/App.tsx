import { Admin, Resource } from "react-admin";
import { dataProvider } from "./dataProvider";
import { Layout } from "./Layout";
import {
  CompanyList,
  CompanyCreate,
  CompanyEdit,
  CompanyShow,
} from "./resources/companies";
import {
  ContactList,
  ContactCreate,
  ContactEdit,
  ContactShow,
} from "./resources/contacts";
import {
  OpportunityList,
  OpportunityCreate,
  OpportunityEdit,
  OpportunityShow,
} from "./resources/opportunities";
import {
  MessageDraftList,
  MessageDraftCreate,
  MessageDraftEdit,
  MessageDraftShow,
} from "./resources/messageDrafts";
import {
  OfferList,
  OfferCreate,
  OfferEdit,
  OfferShow,
} from "./resources/offers";
import {
  AcademyResourceList,
  AcademyResourceCreate,
  AcademyResourceEdit,
  AcademyResourceShow,
} from "./resources/academyResources";
import {
  ComplianceEventList,
  ComplianceEventCreate,
  ComplianceEventShow,
} from "./resources/complianceEvents";
import {
  FollowUpList,
  FollowUpCreate,
  FollowUpEdit,
  FollowUpShow,
} from "./resources/followUps";

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
    <Resource
      name="contacts"
      list={ContactList}
      create={ContactCreate}
      edit={ContactEdit}
      show={ContactShow}
    />
    <Resource
      name="opportunities"
      list={OpportunityList}
      create={OpportunityCreate}
      edit={OpportunityEdit}
      show={OpportunityShow}
    />
    <Resource
      name="offers"
      list={OfferList}
      create={OfferCreate}
      edit={OfferEdit}
      show={OfferShow}
    />
    <Resource
      name="academy-resources"
      list={AcademyResourceList}
      create={AcademyResourceCreate}
      edit={AcademyResourceEdit}
      show={AcademyResourceShow}
    />
    <Resource
      name="message-drafts"
      list={MessageDraftList}
      create={MessageDraftCreate}
      edit={MessageDraftEdit}
      show={MessageDraftShow}
    />
    <Resource
      name="follow-ups"
      list={FollowUpList}
      create={FollowUpCreate}
      edit={FollowUpEdit}
      show={FollowUpShow}
    />
    <Resource
      name="compliance-events"
      list={ComplianceEventList}
      create={ComplianceEventCreate}
      show={ComplianceEventShow}
    />
  </Admin>
);
