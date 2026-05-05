import {
  BooleanField,
  Datagrid,
  DateField,
  List,
  ReferenceField,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const EVENT_TYPE_CHOICES = [
  { id: "contact_collected", name: "Contact Collected" },
  { id: "email_verified", name: "Email Verified" },
  { id: "message_generated", name: "Message Generated" },
  { id: "message_approved", name: "Message Approved" },
  { id: "message_sent", name: "Message Sent" },
  { id: "opt_out_requested", name: "Opt-Out Requested" },
  { id: "data_deleted", name: "Data Deleted" },
];

const SOURCE_CHOICES = [
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

const complianceEventFilters = [
  <TextInput source="company_id" label="Company ID" key="company_id" />,
  <TextInput source="contact_id" label="Contact ID" key="contact_id" />,
  <TextInput
    source="opportunity_id"
    label="Opportunity ID"
    key="opportunity_id"
  />,
  <SelectInput
    source="event_type"
    label="Event Type"
    choices={EVENT_TYPE_CHOICES}
    key="event_type"
  />,
  <SelectInput
    source="source"
    label="Source"
    choices={SOURCE_CHOICES}
    key="source"
  />,
  <SelectInput
    source="opt_out_status"
    label="Opt-Out Status"
    choices={[
      { id: "true", name: "Yes" },
      { id: "false", name: "No" },
    ]}
    key="opt_out_status"
  />,
];

export const ComplianceEventList = () => (
  <List filters={complianceEventFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="event_type" />
      <TextField source="source" />
      <ReferenceField
        source="company_id"
        reference="companies"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="contact_id"
        reference="contacts"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="opportunity_id"
        reference="opportunities"
        link="show"
        emptyText="N/A"
      />
      <BooleanField source="opt_out_status" />
      <DateField source="created_at" showTime />
    </Datagrid>
  </List>
);
