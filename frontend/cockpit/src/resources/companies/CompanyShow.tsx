import {
  DateField,
  EditButton,
  ListButton,
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

export const CompanyShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <TextField source="name" />
      <TextField source="slug" />
      <TextField source="website_url" label="Website URL" />
      <TextField source="domain" />
      <TextField source="company_type" label="Type" />
      <TextField source="sector" />
      <TextField source="size_label" label="Size" />
      <TextField source="employee_count" label="Employee Count" />
      <TextField source="city" />
      <TextField source="region" />
      <TextField source="country" />
      <TextField source="source" />
      <TextField source="source_url" label="Source URL" />
      <TextField source="notes" />
      <TextField source="status" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
