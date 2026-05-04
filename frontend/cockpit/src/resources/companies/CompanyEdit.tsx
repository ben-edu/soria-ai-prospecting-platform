import {
  Edit,
  NumberInput,
  SelectInput,
  SimpleForm,
  TextInput,
  TopToolbar,
  ListButton,
  ShowButton,
} from "react-admin";

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

const SOURCE_CHOICES = [
  { id: "manual", name: "Manual" },
  { id: "france_travail", name: "France Travail" },
  { id: "company_website", name: "Company Website" },
  { id: "linkedin_manual", name: "LinkedIn Manual" },
  { id: "csv", name: "CSV Import" },
  { id: "hunter", name: "Hunter" },
  { id: "dropcontact", name: "Dropcontact" },
  { id: "soria_website_form", name: "SORIA Website Form" },
  { id: "academy", name: "Academy" },
  { id: "openproject", name: "OpenProject" },
  { id: "other", name: "Other" },
];

const STATUS_CHOICES = [
  { id: "new", name: "New" },
  { id: "to_review", name: "To Review" },
  { id: "qualified", name: "Qualified" },
  { id: "not_relevant", name: "Not Relevant" },
  { id: "contacted", name: "Contacted" },
  { id: "active_opportunity", name: "Active Opportunity" },
  { id: "closed", name: "Closed" },
];

const SIZE_CHOICES = [
  { id: "micro", name: "Micro (1-9)" },
  { id: "small", name: "Small (10-49)" },
  { id: "medium", name: "Medium (50-249)" },
  { id: "large", name: "Large (250-999)" },
  { id: "enterprise", name: "Enterprise (1000+)" },
];

const EditActions = () => (
  <TopToolbar>
    <ShowButton />
    <ListButton />
  </TopToolbar>
);

export const CompanyEdit = () => (
  <Edit actions={<EditActions />}>
    <SimpleForm>
      <TextInput source="name" fullWidth />
      <TextInput source="slug" fullWidth />
      <TextInput source="website_url" label="Website URL" fullWidth />
      <TextInput source="domain" fullWidth />
      <SelectInput
        source="company_type"
        label="Type"
        choices={COMPANY_TYPE_CHOICES}
      />
      <TextInput source="sector" fullWidth />
      <SelectInput source="size_label" label="Size" choices={SIZE_CHOICES} />
      <NumberInput source="employee_count" label="Employee Count" />
      <TextInput source="city" />
      <TextInput source="region" />
      <TextInput source="country" />
      <SelectInput source="source" choices={SOURCE_CHOICES} />
      <TextInput source="source_url" label="Source URL" fullWidth />
      <TextInput source="notes" multiline rows={4} fullWidth />
      <SelectInput source="status" choices={STATUS_CHOICES} />
    </SimpleForm>
  </Edit>
);
