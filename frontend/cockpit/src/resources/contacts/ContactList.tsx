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

const EMAIL_VERIFICATION_CHOICES = [
  { id: "unknown", name: "Unknown" },
  { id: "not_checked", name: "Not Checked" },
  { id: "valid", name: "Valid" },
  { id: "invalid", name: "Invalid" },
  { id: "risky", name: "Risky" },
];

const OPT_OUT_CHOICES = [
  { id: "true", name: "Opted Out" },
  { id: "false", name: "Not Opted Out" },
];

const contactFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <TextInput source="company_id" label="Company ID" key="company_id" />,
  <SelectInput
    source="contact_type"
    label="Contact Type"
    choices={CONTACT_TYPE_CHOICES}
    key="contact_type"
  />,
  <SelectInput
    source="email_verification_status"
    label="Email Verification"
    choices={EMAIL_VERIFICATION_CHOICES}
    key="email_verification_status"
  />,
  <SelectInput
    source="opt_out"
    label="Opt Out"
    choices={OPT_OUT_CHOICES}
    key="opt_out"
  />,
];

export const ContactList = () => (
  <List filters={contactFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="full_name" />
      <ReferenceField source="company_id" reference="companies" link="show" />
      <TextField source="role_title" />
      <TextField source="email" />
      <TextField source="contact_type" />
      <TextField source="email_verification_status" />
      <BooleanField source="is_primary" />
      <BooleanField source="opt_out" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
