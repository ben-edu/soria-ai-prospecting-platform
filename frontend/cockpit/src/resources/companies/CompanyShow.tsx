import {
  DateField,
  Datagrid,
  EditButton,
  ListButton,
  ReferenceManyField,
  Show,
  Tab,
  TabbedShowLayout,
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
    <TabbedShowLayout>
      <Tab label="Details">
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
      </Tab>
      <Tab label="Contacts" path="contacts">
        <ReferenceManyField
          reference="contacts"
          target="company_id"
          label="Contacts"
        >
          <Datagrid rowClick={false} bulkActionButtons={false}>
            <TextField source="full_name" />
            <TextField source="role_title" />
            <TextField source="email" />
            <TextField source="contact_type" />
            <TextField source="email_verification_status" />
          </Datagrid>
        </ReferenceManyField>
      </Tab>
      <Tab label="Opportunities" path="opportunities">
        <ReferenceManyField
          reference="opportunities"
          target="company_id"
          label="Opportunities"
        >
          <Datagrid rowClick={false} bulkActionButtons={false}>
            <TextField source="title" />
            <TextField source="opportunity_type" />
            <TextField source="status" />
            <TextField source="priority" />
            <TextField source="score" />
          </Datagrid>
        </ReferenceManyField>
      </Tab>
    </TabbedShowLayout>
  </Show>
);
