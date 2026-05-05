import {
  BooleanField,
  Datagrid,
  DateField,
  List,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const RESOURCE_TYPE_CHOICES = [
  { id: "guide", name: "Guide" },
  { id: "article", name: "Article" },
  { id: "checklist", name: "Checklist" },
  { id: "course", name: "Course" },
  { id: "lab", name: "Lab" },
  { id: "workshop", name: "Workshop" },
  { id: "project", name: "Project" },
  { id: "moodle_path", name: "Moodle Path" },
  { id: "support_material", name: "Support Material" },
  { id: "case_study", name: "Case Study" },
];

const LEVEL_CHOICES = [
  { id: "beginner", name: "Beginner" },
  { id: "intermediate", name: "Intermediate" },
  { id: "advanced", name: "Advanced" },
  { id: "mixed", name: "Mixed" },
];

const resourceFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <SelectInput
    source="resource_type"
    label="Type"
    choices={RESOURCE_TYPE_CHOICES}
    key="resource_type"
  />,
  <SelectInput
    source="level"
    label="Level"
    choices={LEVEL_CHOICES}
    key="level"
  />,
  <SelectInput
    source="active"
    label="Published"
    choices={[
      { id: "true", name: "Published" },
      { id: "false", name: "Unpublished" },
    ]}
    key="active"
  />,
];

export const AcademyResourceList = () => (
  <List filters={resourceFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="title" />
      <TextField source="resource_type" />
      <TextField source="level" />
      <BooleanField source="is_published" label="Published" />
      <BooleanField source="is_free" label="Free" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
