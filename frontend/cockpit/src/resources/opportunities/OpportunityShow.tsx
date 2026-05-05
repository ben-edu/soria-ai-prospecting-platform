import {
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

export const OpportunityShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <ReferenceField source="company_id" reference="companies" link="show" />
      <ReferenceField
        source="contact_id"
        reference="contacts"
        link="show"
        emptyText="N/A"
      />
      <TextField source="offer_id" emptyText="N/A" />
      <TextField source="academy_resource_id" emptyText="N/A" />
      <TextField source="title" />
      <TextField source="opportunity_type" />
      <TextField source="description" />
      <TextField source="detected_need" />
      <TextField source="source" />
      <TextField source="source_url" />
      <DateField source="source_published_at" showTime emptyText="N/A" />
      <TextField source="location" />
      <TextField source="language" />
      <TextField source="status" />
      <TextField source="priority" />
      <TextField source="score" emptyText="N/A" />
      <TextField source="recommended_landing_page" />
      <TextField source="next_action" />
      <TextField source="notes" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
