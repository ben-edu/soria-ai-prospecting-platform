import {
  BooleanInput,
  Edit,
  NumberInput,
  SimpleForm,
  TextInput,
  TopToolbar,
  ListButton,
  ShowButton,
} from "react-admin";

const EditActions = () => (
  <TopToolbar>
    <ShowButton />
    <ListButton />
  </TopToolbar>
);

export const OfferEdit = () => (
  <Edit actions={<EditActions />}>
    <SimpleForm>
      <TextInput source="name" fullWidth />
      <TextInput source="slug" fullWidth />
      <TextInput source="category_id" label="Category ID" fullWidth />
      <TextInput
        source="short_description"
        label="Short Description"
        fullWidth
      />
      <TextInput
        source="full_description"
        label="Full Description"
        multiline
        rows={4}
        fullWidth
      />
      <TextInput source="landing_page_url" label="Landing Page URL" fullWidth />
      <TextInput
        source="target_audience"
        label="Target Audience (JSON)"
        fullWidth
      />
      <TextInput source="keywords" label="Keywords (JSON)" fullWidth />
      <NumberInput source="priority" />
      <BooleanInput source="is_active" label="Active" />
    </SimpleForm>
  </Edit>
);
