import {
  Datagrid,
  DateField,
  List,
  ReferenceField,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const MESSAGE_TYPE_CHOICES = [
  { id: "prospecting_email", name: "Prospecting Email" },
  { id: "linkedin_message", name: "LinkedIn Message" },
  { id: "follow_up_email", name: "Follow-Up Email" },
  { id: "training_proposal", name: "Training Proposal" },
  { id: "devops_proposal", name: "DevOps Proposal" },
  { id: "cybersecurity_proposal", name: "Cybersecurity Proposal" },
  { id: "academy_invitation", name: "Academy Invitation" },
  { id: "motivation_letter", name: "Motivation Letter" },
  { id: "cv_summary", name: "CV Summary" },
  { id: "internal_note", name: "Internal Note" },
];

const STATUS_CHOICES = [
  { id: "draft", name: "Draft" },
  { id: "needs_review", name: "Needs Review" },
  { id: "approved", name: "Approved" },
  { id: "rejected", name: "Rejected" },
  { id: "sent_manually", name: "Sent Manually" },
  { id: "sent_by_system", name: "Sent By System" },
  { id: "archived", name: "Archived" },
];

const messageDraftFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <TextInput
    source="opportunity_id"
    label="Opportunity ID"
    key="opportunity_id"
  />,
  <TextInput source="contact_id" label="Contact ID" key="contact_id" />,
  <SelectInput
    source="status"
    label="Status"
    choices={STATUS_CHOICES}
    key="status"
  />,
  <SelectInput
    source="message_type"
    label="Message Type"
    choices={MESSAGE_TYPE_CHOICES}
    key="message_type"
  />,
  <TextInput source="language" label="Language" key="language" />,
];

export const MessageDraftList = () => (
  <List filters={messageDraftFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="subject" />
      <ReferenceField
        source="opportunity_id"
        reference="opportunities"
        link="show"
      />
      <ReferenceField
        source="contact_id"
        reference="contacts"
        link="show"
        emptyText="N/A"
      />
      <TextField source="message_type" />
      <TextField source="language" />
      <TextField source="status" />
      <TextField source="generated_by" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
