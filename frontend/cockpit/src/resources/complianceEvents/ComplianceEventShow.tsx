import {
  BooleanField,
  DateField,
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
  </TopToolbar>
);

export const ComplianceEventShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <TextField source="id" />
      <TextField source="event_type" />
      <TextField source="source" />
      <ReferenceField
        source="company_id"
        reference="companies"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="contact_id"
        reference="contacts"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="opportunity_id"
        reference="opportunities"
        link="show"
        emptyText="N/A"
      />
      <TextField source="source_url" emptyText="N/A" />
      <TextField source="reason_for_contact" emptyText="N/A" />
      <TextField source="professional_relevance" emptyText="N/A" />
      <BooleanField source="opt_out_status" />
      <TextField source="notes" emptyText="N/A" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
