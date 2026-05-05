import {
  BooleanField,
  DateField,
  EditButton,
  ListButton,
  NumberField,
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

export const OfferShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <TextField source="name" />
      <TextField source="slug" />
      <TextField source="category_id" label="Category ID" />
      <TextField source="short_description" label="Short Description" />
      <TextField source="full_description" label="Full Description" />
      <TextField source="landing_page_url" label="Landing Page URL" />
      <TextField source="target_audience" label="Target Audience" />
      <TextField source="keywords" />
      <NumberField source="priority" />
      <BooleanField source="is_active" label="Active" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
