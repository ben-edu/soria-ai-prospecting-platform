import {
  Datagrid,
  DateField,
  List,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const COMPANY_STATUS_CHOICES = [
  { id: "new", name: "New" },
  { id: "to_review", name: "To Review" },
  { id: "qualified", name: "Qualified" },
  { id: "not_relevant", name: "Not Relevant" },
  { id: "contacted", name: "Contacted" },
  { id: "active_opportunity", name: "Active Opportunity" },
  { id: "closed", name: "Closed" },
];

const COMPANY_TYPE_CHOICES = [
  { id: "training_center", name: "Training Center" },
  { id: "school", name: "School" },
  { id: "cfa", name: "CFA" },
  { id: "university", name: "University" },
  { id: "pme", name: "PME" },
  { id: "startup", name: "Startup" },
  { id: "web_agency", name: "Web Agency" },
  { id: "it_company", name: "IT Company" },
  { id: "recruiter", name: "Recruiter" },
  { id: "public_organization", name: "Public Organization" },
  { id: "nonprofit", name: "Nonprofit" },
  { id: "enterprise", name: "Enterprise" },
  { id: "unknown", name: "Unknown" },
];

const companyFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <SelectInput
    source="status"
    label="Status"
    choices={COMPANY_STATUS_CHOICES}
    alwaysOn
    key="status"
  />,
  <SelectInput
    source="company_type"
    label="Type"
    choices={COMPANY_TYPE_CHOICES}
    key="company_type"
  />,
  <TextInput source="country" label="Country" key="country" />,
];

export const CompanyList = () => (
  <List filters={companyFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="name" />
      <TextField source="company_type" />
      <TextField source="status" />
      <TextField source="city" />
      <TextField source="country" />
      <TextField source="domain" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
