import {
  BooleanField,
  Datagrid,
  DateField,
  List,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const SOURCE_TYPE_CHOICES = [
  { id: "manual", name: "Manual" },
  { id: "france_travail", name: "France Travail" },
  { id: "company_website", name: "Company Website" },
  { id: "linkedin_manual", name: "LinkedIn Manual" },
  { id: "csv", name: "CSV" },
  { id: "hunter", name: "Hunter" },
  { id: "dropcontact", name: "Dropcontact" },
  { id: "soria_website_form", name: "SORIA Website Form" },
  { id: "academy", name: "Academy" },
  { id: "openproject", name: "OpenProject" },
  { id: "other", name: "Other" },
];

const sourceRecordFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <TextInput source="source_name" label="Source Name" key="source_name" />,
  <SelectInput
    source="source_type"
    label="Source Type"
    choices={SOURCE_TYPE_CHOICES}
    key="source_type"
  />,
  <TextInput source="external_id" label="External ID" key="external_id" />,
  <SelectInput
    source="processed"
    label="Processed"
    choices={[
      { id: "true", name: "Yes" },
      { id: "false", name: "No" },
    ]}
    key="processed"
  />,
];

export const SourceRecordList = () => (
  <List filters={sourceRecordFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <DateField source="imported_at" showTime />
      <TextField source="source_name" />
      <TextField source="source_type" />
      <TextField source="external_id" />
      <BooleanField source="processed" />
      <TextField source="source_url" emptyText="N/A" />
      <TextField source="processing_notes" emptyText="N/A" />
    </Datagrid>
  </List>
);
