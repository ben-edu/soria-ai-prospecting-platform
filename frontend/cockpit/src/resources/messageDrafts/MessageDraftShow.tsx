import { useState } from "react";
import {
  DateField,
  EditButton,
  ListButton,
  ReferenceField,
  Show,
  SimpleShowLayout,
  TextField,
  TopToolbar,
  useNotify,
  useRefresh,
  useShowContext,
} from "react-admin";
import { Button, Stack } from "@mui/material";
import { API_BASE_URL } from "../../config";

const WorkflowActions = () => {
  const { record, isLoading } = useShowContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = useState<string | null>(null);

  if (isLoading || !record) return null;

  type Status = string;
  type ActionDef = {
    label: string;
    action: string;
    allowed: Status[];
  };

  const actions: ActionDef[] = [
    {
      label: "Submit for Review",
      action: "submit-review",
      allowed: ["draft", "rejected"],
    },
    {
      label: "Approve",
      action: "approve",
      allowed: ["needs_review"],
    },
    {
      label: "Reject",
      action: "reject",
      allowed: ["needs_review"],
    },
    {
      label: "Mark Sent Manually",
      action: "mark-sent-manually",
      allowed: ["approved"],
    },
    {
      label: "Archive",
      action: "archive",
      allowed: ["draft", "needs_review", "rejected", "approved"],
    },
  ];

  const visible = actions.filter((a) => a.allowed.includes(record.status));

  if (visible.length === 0) return null;

  const handleAction = async (action: string) => {
    setLoading(action);
    try {
      const res = await fetch(
        `${API_BASE_URL}/message-drafts/${record.id}/${action}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
      );

      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try {
          const parsed = JSON.parse(text);
          if (parsed.detail) detail = parsed.detail;
        } catch {
          /* ignore */
        }
        notify(detail, { type: "error" });
        return;
      }

      notify(`Action "${action}" completed successfully`, { type: "success" });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
      {visible.map((a) => (
        <Button
          key={a.action}
          variant="contained"
          color={
            a.action === "approve"
              ? "success"
              : a.action === "reject"
                ? "error"
                : "primary"
          }
          onClick={() => handleAction(a.action)}
          disabled={loading !== null}
        >
          {loading === a.action ? "Processing..." : a.label}
        </Button>
      ))}
    </Stack>
  );
};

const ShowActions = () => (
  <TopToolbar>
    <ListButton />
    <EditButton />
  </TopToolbar>
);

export const MessageDraftShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <WorkflowActions />
      <TextField source="id" />
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
      <TextField source="subject" />
      <TextField source="body" />
      <TextField source="tone" />
      <TextField source="status" />
      <TextField source="generated_by" />
      <TextField source="model_name" emptyText="N/A" />
      <TextField source="prompt_version" emptyText="N/A" />
      <TextField source="review_notes" emptyText="N/A" />
      <DateField source="approved_at" showTime emptyText="N/A" />
      <DateField source="sent_at" showTime emptyText="N/A" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
