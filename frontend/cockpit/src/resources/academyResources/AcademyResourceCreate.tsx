import {
  BooleanInput,
  Create,
  SelectInput,
  SimpleForm,
  TextInput,
  required,
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

export const AcademyResourceCreate = () => (
  <Create>
    <SimpleForm>
      <TextInput source="title" validate={required()} fullWidth />
      <TextInput source="slug" validate={required()} fullWidth />
      <TextInput source="category_id" label="Category ID" fullWidth />
      <SelectInput
        source="resource_type"
        label="Type"
        choices={RESOURCE_TYPE_CHOICES}
        defaultValue="guide"
      />
      <SelectInput
        source="level"
        choices={LEVEL_CHOICES}
        defaultValue="beginner"
      />
      <TextInput
        source="short_description"
        label="Short Description"
        fullWidth
      />
      <TextInput source="content" multiline rows={4} fullWidth />
      <TextInput
        source="target_audience"
        label="Target Audience (JSON)"
        fullWidth
      />
      <TextInput source="technologies" label="Technologies (JSON)" fullWidth />
      <TextInput source="public_url" label="Public URL" fullWidth />
      <TextInput source="academy_url" label="Academy URL" fullWidth />
      <TextInput source="moodle_course_id" label="Moodle Course ID" />
      <BooleanInput source="is_free" label="Free" defaultValue />
      <BooleanInput source="is_published" label="Published" />
    </SimpleForm>
  </Create>
);
