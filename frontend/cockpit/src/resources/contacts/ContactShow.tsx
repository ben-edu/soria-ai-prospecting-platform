import {
  BooleanField,
  DateField,
  EditButton,
  ListButton,
  ReferenceField,
  Show,
  SimpleShowLayout,
  TextField,
  TopToolbar,
} from "react-admin";

const ShowActions = () => (
  <TopToolbar>
    <ListButton />
    <EditButton />
  </TopToolbar>
);

export const ContactShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <ReferenceField source="company_id" reference="companies" link="show" />
      <TextField source="first_name" />
      <TextField source="last_name" />
      <TextField source="full_name" />
      <TextField source="role_title" />
      <TextField source="email" />
      <TextField source="phone" />
      <TextField source="linkedin_url" />
      <TextField source="contact_type" />
      <TextField source="source" />
      <TextField source="source_url" />
      <TextField source="email_verification_status" />
      <BooleanField source="is_primary" />
      <BooleanField source="opt_out" />
      <TextField source="notes" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
