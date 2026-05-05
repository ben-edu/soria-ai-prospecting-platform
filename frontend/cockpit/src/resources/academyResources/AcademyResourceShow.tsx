import {
  BooleanField,
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

export const AcademyResourceShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <TextField source="title" />
      <TextField source="slug" />
      <TextField source="category_id" label="Category ID" />
      <TextField source="resource_type" label="Type" />
      <TextField source="level" />
      <TextField source="short_description" label="Short Description" />
      <TextField source="content" />
      <TextField source="target_audience" label="Target Audience" />
      <TextField source="technologies" />
      <TextField source="public_url" label="Public URL" />
      <TextField source="academy_url" label="Academy URL" />
      <TextField source="moodle_course_id" label="Moodle Course ID" />
      <BooleanField source="is_free" label="Free" />
      <BooleanField source="is_published" label="Published" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
