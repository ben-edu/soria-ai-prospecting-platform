import { useState } from "react";
import {
  DateTimeInput,
  Edit,
  ListButton,
  NumberInput,
  ReferenceInput,
  SelectInput,
  ShowButton,
  SimpleForm,
  TextInput,
  TopToolbar,
  useNotify,
  useRecordContext,
  useRefresh,
} from "react-admin";
import { Button } from "@mui/material";
import { API_BASE_URL } from "../../config";

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

const SOURCE_CHOICES = [
  { id: "manual", name: "Manual" },
  { id: "france_travail", name: "France Travail" },
  { id: "company_website", name: "Company Website" },
  { id: "linkedin_manual", name: "LinkedIn Manual" },
  { id: "csv", name: "CSV Import" },
  { id: "hunter", name: "Hunter" },
  { id: "dropcontact", name: "Dropcontact" },
  { id: "soria_website_form", name: "SORIA Website Form" },
  { id: "academy", name: "Academy" },
  { id: "openproject", name: "OpenProject" },
  { id: "other", name: "Other" },
];

const STATUS_CHOICES = [
  { id: "imported_pending_review", name: "Imported (Pending Review)" },
  { id: "new", name: "New" },
  { id: "to_analyze", name: "To Analyze" },
  { id: "scored", name: "Scored" },
  { id: "interesting", name: "Interesting" },
  { id: "not_relevant", name: "Not Relevant" },
  { id: "draft_needed", name: "Draft Needed" },
  { id: "contact_to_find", name: "Contact To Find" },
  { id: "contact_found", name: "Contact Found" },
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

const B2BQualifyButton = () => {
  const record = useRecordContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = useState(false);

  if (!record) return null;

  const handleQualify = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/b2b/opportunities/${record.id}/qualify`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
      );
      const payload = await response.json();
      if (!response.ok) {
        notify(payload.detail ?? "B2B qualification failed", { type: "error" });
        return;
      }
      notify(
        `MVCS B2B score ${payload.score}/100 — ${payload.qualified ? "qualified" : "not qualified"} — ${payload.matched_offer_name}`,
        { type: payload.qualified ? "success" : "warning" },
      );
      refresh();
    } catch (error: unknown) {
      notify(error instanceof Error ? error.message : "B2B qualification failed", {
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button onClick={handleQualify} disabled={loading} variant="contained" color="secondary">
      {loading ? "Qualifying..." : "Qualify B2B"}
    </Button>
  );
};

const EditActions = () => (
  <TopToolbar>
    <B2BQualifyButton />
    <ShowButton />
    <ListButton />
  </TopToolbar>
);

export const OpportunityEdit = () => (
  <Edit actions={<EditActions />}>
    <SimpleForm>
      <TextInput source="title" fullWidth />
      <ReferenceInput source="company_id" reference="companies" />
      <ReferenceInput source="contact_id" reference="contacts" />
      <SelectInput source="opportunity_type" label="Type" choices={OPPORTUNITY_TYPE_CHOICES} />
      <TextInput source="description" multiline rows={4} fullWidth />
      <TextInput source="detected_need" multiline rows={3} fullWidth />
      <SelectInput source="source" choices={SOURCE_CHOICES} />
      <TextInput source="source_url" label="Source URL" fullWidth />
      <DateTimeInput source="source_published_at" label="Public signal date" />
      <TextInput source="location" />
      <TextInput source="language" />
      <SelectInput source="status" choices={STATUS_CHOICES} />
      <SelectInput source="priority" choices={PRIORITY_CHOICES} />
      <NumberInput source="score" min={0} max={100} />
      <TextInput source="recommended_landing_page" label="Recommended Landing Page" fullWidth />
      <TextInput source="next_action" label="Next Action" fullWidth />
      <TextInput source="offer_id" label="Offer ID" />
      <TextInput source="academy_resource_id" label="Academy Resource ID" />
      <TextInput source="openproject_work_package_id" label="OpenProject Work Package ID" />
      <TextInput source="notes" multiline rows={4} fullWidth />
    </SimpleForm>
  </Edit>
);
