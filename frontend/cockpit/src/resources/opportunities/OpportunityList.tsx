import {
  Datagrid,
  DateField,
  List,
  NumberInput,
  ReferenceField,
  SelectInput,
  TextField,
  TextInput,
} from "react-admin";

const OPPORTUNITY_TYPE_CHOICES = [
  { id: "formation", name: "Formation" },
  { id: "devops_cloud", name: "DevOps / Cloud" },
  { id: "cybersecurity_soc", name: "Cybersecurity / SOC" },
  { id: "iam_sso", name: "IAM / SSO" },
  { id: "monitoring", name: "Monitoring" },
  { id: "freelance", name: "Freelance" },
  { id: "job", name: "Job" },
  { id: "academic", name: "Academic" },
  { id: "partnership", name: "Partnership" },
  { id: "academy", name: "Academy" },
  { id: "other", name: "Other" },
];

const STATUS_CHOICES = [
  { id: "new", name: "New" },
  { id: "imported_pending_review", name: "Imported (Pending Review)" },
  { id: "to_analyze", name: "To Analyze" },
  { id: "scored", name: "Scored" },
  { id: "interesting", name: "Interesting" },
  { id: "not_relevant", name: "Not Relevant" },
  { id: "contact_to_find", name: "Contact To Find" },
  { id: "contact_found", name: "Contact Found" },
  { id: "draft_needed", name: "Draft Needed" },
  { id: "draft_ready", name: "Draft Ready" },
  { id: "waiting_validation", name: "Waiting Validation" },
  { id: "approved", name: "Approved" },
  { id: "sent", name: "Sent" },
  { id: "follow_up_needed", name: "Follow-Up Needed" },
  { id: "response_received", name: "Response Received" },
  { id: "meeting_scheduled", name: "Meeting Scheduled" },
  { id: "converted", name: "Converted" },
  { id: "lost", name: "Lost" },
  { id: "closed", name: "Closed" },
];

const PRIORITY_CHOICES = [
  { id: "low", name: "Low" },
  { id: "medium", name: "Medium" },
  { id: "high", name: "High" },
  { id: "urgent", name: "Urgent" },
];

const opportunityFilters = [
  <TextInput source="search" label="Search" alwaysOn key="search" />,
  <TextInput source="company_id" label="Company ID" key="company_id" />,
  <TextInput source="contact_id" label="Contact ID" key="contact_id" />,
  <SelectInput
    source="opportunity_type"
    label="Type"
    choices={OPPORTUNITY_TYPE_CHOICES}
    key="opportunity_type"
  />,
  <SelectInput
    source="status"
    label="Status"
    choices={STATUS_CHOICES}
    key="status"
  />,
  <SelectInput
    source="priority"
    label="Priority"
    choices={PRIORITY_CHOICES}
    key="priority"
  />,
  <NumberInput source="min_score" label="Min Score" key="min_score" />,
];

export const OpportunityList = () => (
  <List filters={opportunityFilters}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="title" />
      <ReferenceField source="company_id" reference="companies" link="show" />
      <ReferenceField source="contact_id" reference="contacts" link="show" />
      <TextField source="opportunity_type" />
      <TextField source="status" />
      <TextField source="priority" />
      <TextField source="score" />
      <TextField source="language" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </Datagrid>
  </List>
);
