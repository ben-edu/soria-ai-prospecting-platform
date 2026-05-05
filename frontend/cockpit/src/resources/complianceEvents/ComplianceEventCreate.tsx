import {
  BooleanInput,
  Create,
  ReferenceInput,
  required,
  SelectInput,
  SimpleForm,
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

export const ComplianceEventCreate = () => (
  <Create>
    <SimpleForm>
      <ReferenceInput source="company_id" reference="companies" />
      <ReferenceInput source="contact_id" reference="contacts" />
      <ReferenceInput source="opportunity_id" reference="opportunities" />
      <SelectInput
        source="event_type"
        label="Event Type"
        choices={EVENT_TYPE_CHOICES}
        validate={required()}
      />
      <SelectInput
        source="source"
        label="Source"
        choices={SOURCE_CHOICES}
        defaultValue="manual"
      />
      <TextInput source="source_url" label="Source URL" fullWidth />
      <TextInput
        source="reason_for_contact"
        label="Reason for Contact"
        multiline
        rows={3}
        fullWidth
        validate={required()}
      />
      <TextInput
        source="professional_relevance"
        label="Professional Relevance"
        multiline
        rows={3}
        fullWidth
      />
      <BooleanInput
        source="opt_out_status"
        label="Opt-Out Status"
        defaultValue={false}
      />
      <TextInput source="notes" multiline rows={3} fullWidth />
    </SimpleForm>
  </Create>
);
