import {
  BooleanInput,
  Create,
  NumberInput,
  SimpleForm,
  TextInput,
  required,
} from "react-admin";

export const OfferCreate = () => (
  <Create>
    <SimpleForm>
      <TextInput source="name" validate={required()} fullWidth />
      <TextInput source="slug" validate={required()} fullWidth />
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
      <NumberInput source="priority" defaultValue={0} />
      <BooleanInput source="is_active" label="Active" defaultValue />
    </SimpleForm>
  </Create>
);
