import {
  Datagrid,
  DateField,
  List,
  ReferenceField,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const ACTION_TYPE_CHOICES = [
  { id: "send_first_message", name: "Send First Message" },
  { id: "send_follow_up", name: "Send Follow-Up" },
  { id: "call", name: "Call" },
  { id: "linkedin_manual_message", name: "LinkedIn Manual Message" },
  { id: "prepare_proposal", name: "Prepare Proposal" },
  { id: "schedule_meeting", name: "Schedule Meeting" },
  { id: "update_openproject", name: "Update OpenProject" },
  { id: "close_opportunity", name: "Close Opportunity" },
];

const STATUS_CHOICES = [
  { id: "planned", name: "Planned" },
  { id: "done", name: "Done" },
  { id: "cancelled", name: "Cancelled" },
  { id: "overdue", name: "Overdue" },
];

const followUpFilters = [
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
    source="action_type"
    label="Action Type"
    choices={ACTION_TYPE_CHOICES}
    key="action_type"
  />,
];

export const FollowUpList = () => (
  <List filters={followUpFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <DateField source="due_date" showTime />
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
      <TextField source="action_type" />
      <TextField source="status" />
      <TextField source="openproject_work_package_id" emptyText="N/A" />
      <DateField source="created_at" showTime />
    </Datagrid>
  </List>
);
