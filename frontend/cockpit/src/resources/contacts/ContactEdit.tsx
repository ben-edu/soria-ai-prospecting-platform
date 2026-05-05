import {
  BooleanInput,
  Edit,
  ReferenceInput,
  SelectInput,
  SimpleForm,
  TextInput,
  TopToolbar,
  ListButton,
  ShowButton,
} from "react-admin";

const CONTACT_TYPE_CHOICES = [
  { id: "director", name: "Director" },
  { id: "training_manager", name: "Training Manager" },
  { id: "it_manager", name: "IT Manager" },
  { id: "hr", name: "HR" },
  { id: "recruiter", name: "Recruiter" },
  { id: "technical_lead", name: "Technical Lead" },
  { id: "founder", name: "Founder" },
  { id: "generic_contact", name: "Generic Contact" },
  { id: "academic_contact", name: "Academic Contact" },
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

const EMAIL_VERIFICATION_CHOICES = [
  { id: "unknown", name: "Unknown" },
  { id: "not_checked", name: "Not Checked" },
  { id: "valid", name: "Valid" },
  { id: "invalid", name: "Invalid" },
  { id: "risky", name: "Risky" },
];

const EditActions = () => (
  <TopToolbar>
    <ShowButton />
    <ListButton />
  </TopToolbar>
);

export const ContactEdit = () => (
  <Edit actions={<EditActions />}>
    <SimpleForm>
      <ReferenceInput source="company_id" reference="companies" />
      <TextInput source="first_name" />
      <TextInput source="last_name" />
      <TextInput source="full_name" />
      <TextInput source="role_title" label="Role / Title" fullWidth />
      <TextInput source="email" type="email" fullWidth />
      <TextInput source="phone" />
      <TextInput source="linkedin_url" label="LinkedIn URL" fullWidth />
      <SelectInput
        source="contact_type"
        label="Contact Type"
        choices={CONTACT_TYPE_CHOICES}
      />
      <SelectInput source="source" choices={SOURCE_CHOICES} />
      <TextInput source="source_url" label="Source URL" fullWidth />
      <SelectInput
        source="email_verification_status"
        label="Email Verification"
        choices={EMAIL_VERIFICATION_CHOICES}
      />
      <BooleanInput source="is_primary" label="Is Primary" />
      <BooleanInput source="opt_out" label="Opted Out" />
      <TextInput source="notes" multiline rows={4} fullWidth />
    </SimpleForm>
  </Edit>
);
