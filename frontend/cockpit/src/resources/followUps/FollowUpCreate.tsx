import {
  Create,
  DateTimeInput,
  ReferenceInput,
  required,
  SelectInput,
  SimpleForm,
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

export const FollowUpCreate = () => (
  <Create>
    <SimpleForm>
      <ReferenceInput
        source="opportunity_id"
        reference="opportunities"
        validate={required()}
      />
      <ReferenceInput source="contact_id" reference="contacts" />
      <DateTimeInput source="due_date" validate={required()} />
      <SelectInput
        source="action_type"
        label="Action Type"
        choices={ACTION_TYPE_CHOICES}
        defaultValue="send_follow_up"
      />
      <SelectInput
        source="status"
        label="Status"
        choices={STATUS_CHOICES}
        defaultValue="planned"
      />
      <TextInput source="notes" fullWidth multiline rows={3} />
      <TextInput
        source="openproject_work_package_id"
        label="OpenProject WP ID"
      />
    </SimpleForm>
  </Create>
);
