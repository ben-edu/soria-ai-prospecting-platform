import {
  BooleanField,
  Datagrid,
  DateField,
  List,
  NumberField,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const offerFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <SelectInput
    source="active"
    label="Active"
    choices={[
      { id: "true", name: "Active" },
      { id: "false", name: "Inactive" },
    ]}
    alwaysOn
    key="active"
  />,
];

export const OfferList = () => (
  <List filters={offerFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="name" />
      <TextField source="slug" />
      <TextField source="short_description" />
      <NumberField source="priority" />
      <BooleanField source="is_active" label="Active" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
