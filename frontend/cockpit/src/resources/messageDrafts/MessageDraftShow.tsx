import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  Stack,
  TextField as MuiTextField,
  Typography,
} from "@mui/material";
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
import { API_BASE_URL } from "../../config";

// ---- Types ----

interface DialogState {
  open: boolean;
  action: string;
  label: string;
}

interface WorkflowAction {
  label: string;
  action: string;
  allowed: string[];
  color?: "primary" | "success" | "error" | "info" | "warning";
}

interface ActionGroup {
  groupLabel: string;
  actions: WorkflowAction[];
}

// ---- Constants ----

const STATUS_COLORS: Record<
  string,
  "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"
> = {
  draft: "default",
  needs_review: "warning",
  approved: "success",
  rejected: "error",
  sent_manually: "info",
  archived: "secondary",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  needs_review: "Needs Review",
  approved: "Approved",
  rejected: "Rejected",
  sent_manually: "Sent Manually",
  archived: "Archived",
};

const ACTION_GROUPS: ActionGroup[] = [
  {
    groupLabel: "Review Submission",
    actions: [
      {
        label: "Submit for Review",
        action: "submit-review",
        allowed: ["draft", "rejected"],
        color: "primary",
      },
    ],
  },
  {
    groupLabel: "Human Decision",
    actions: [
      {
        label: "Approve",
        action: "approve",
        allowed: ["needs_review"],
        color: "success",
      },
      {
        label: "Reject",
        action: "reject",
        allowed: ["needs_review"],
        color: "error",
      },
    ],
  },
  {
    groupLabel: "Sending",
    actions: [
      {
        label: "Mark Sent Manually",
        action: "mark-sent-manually",
        allowed: ["approved"],
        color: "info",
      },
    ],
  },
  {
    groupLabel: "Maintenance",
    actions: [
      {
        label: "Archive",
        action: "archive",
        allowed: ["draft", "needs_review", "rejected", "approved"],
        color: "warning",
      },
    ],
  },
];

// ---- Action Dialog ----

interface ActionDialogProps {
  open: boolean;
  action: string;
  label: string;
  onClose: () => void;
  onConfirm: (reviewNotes: string) => void;
  loading: boolean;
}

const ActionDialog = ({
  open,
  action,
  label,
  onClose,
  onConfirm,
  loading,
}: ActionDialogProps) => {
  const [reviewNotes, setReviewNotes] = useState("");

  const needsReviewNotes =
    action === "submit-review" || action === "approve" || action === "reject";
  const isMarkSent = action === "mark-sent-manually";
  const isArchive = action === "archive";

  const handleClose = () => {
    setReviewNotes("");
    onClose();
  };

  const handleConfirm = () => {
    onConfirm(reviewNotes);
    setReviewNotes("");
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{label}</DialogTitle>
      <DialogContent>
        {isMarkSent && (
          <DialogContentText sx={{ mb: 2 }}>
            This action does <strong>not</strong> send an email. It only records
            that you have sent the message manually outside the system. The
            backend will schedule a follow-up based on this record.
          </DialogContentText>
        )}
        {isArchive && (
          <DialogContentText sx={{ mb: 2 }}>
            Are you sure you want to archive this draft? Note that drafts with
            status &quot;sent manually&quot; cannot be archived.
          </DialogContentText>
        )}
        {needsReviewNotes && (
          <MuiTextField
            autoFocus
            label="Review Notes (optional)"
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            multiline
            rows={3}
            fullWidth
            sx={{ mt: 1 }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color="primary"
          disabled={loading}
        >
          {loading ? "Processing..." : "Confirm"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// ---- Workflow Panel ----

const WorkflowPanel = () => {
  const { record, isLoading } = useShowContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState>({
    open: false,
    action: "",
    label: "",
  });

  if (isLoading || !record) return null;

  const currentStatus = record.status as string;

  const handleActionClick = (actionLabel: string, actionName: string) => {
    setDialog({ open: true, action: actionName, label: actionLabel });
  };

  const handleDialogClose = () => {
    setDialog({ open: false, action: "", label: "" });
  };

  const handleActionConfirm = async (reviewNotes: string) => {
    const action = dialog.action;
    setLoadingAction(action);
    handleDialogClose();
    try {
      const body =
        (action === "submit-review" ||
          action === "approve" ||
          action === "reject") &&
        reviewNotes
          ? JSON.stringify({ review_notes: reviewNotes })
          : JSON.stringify({});

      const res = await fetch(
        `${API_BASE_URL}/message-drafts/${record.id as string}/${action}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
        },
      );

      if (!res.ok) {
        const text = await res.text();
        let detail: string = text;
        try {
          const parsed = JSON.parse(text);
          if (parsed.detail) detail = parsed.detail;
        } catch {
          /* ignore */
        }
        notify(detail, { type: "error" });
        return;
      }

      notify(`Action "${action}" completed successfully`, {
        type: "success",
      });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <>
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold">
              Status:
            </Typography>
            <Chip
              label={STATUS_LABELS[currentStatus] ?? currentStatus}
              color={STATUS_COLORS[currentStatus] ?? "default"}
            />
          </Stack>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            AI/rule-based drafts are never sent automatically. Human review and
            approval is mandatory before any external contact is made.
            &quot;Mark sent manually&quot; records that the message was sent
            outside the system and schedules follow-up through the backend
            workflow.
          </Typography>

          <Divider sx={{ mb: 2 }} />

          {ACTION_GROUPS.map((group) => {
            const visibleActions = group.actions.filter((a) =>
              a.allowed.includes(currentStatus),
            );
            if (visibleActions.length === 0) return null;

            return (
              <Box key={group.groupLabel} sx={{ mb: 1.5 }}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mb: 0.5, display: "block" }}
                >
                  {group.groupLabel}
                </Typography>
                <Stack direction="row" spacing={1}>
                  {visibleActions.map((a) => (
                    <Button
                      key={a.action}
                      variant="contained"
                      color={a.color ?? "primary"}
                      onClick={() => handleActionClick(a.label, a.action)}
                      disabled={loadingAction !== null}
                      size="small"
                    >
                      {loadingAction === a.action ? "Processing..." : a.label}
                    </Button>
                  ))}
                </Stack>
              </Box>
            );
          })}
        </CardContent>
      </Card>

      <ActionDialog
        open={dialog.open}
        action={dialog.action}
        label={dialog.label}
        onClose={handleDialogClose}
        onConfirm={handleActionConfirm}
        loading={loadingAction === dialog.action}
      />
    </>
  );
};

// ---- AI Audit Card ----

const AiAuditCard = () => {
  const { record, isLoading } = useShowContext();

  if (isLoading || !record) return null;

  const fields: Array<{ label: string; source: string }> = [
    { label: "Generated By", source: "generated_by" },
    { label: "AI Provider", source: "ai_provider" },
    { label: "Model Name", source: "model_name" },
    { label: "Prompt Profile", source: "prompt_profile" },
    { label: "Prompt Version", source: "prompt_version" },
  ];

  const hasAnyValue = fields.some((f) => record[f.source]);

  if (!hasAnyValue) return null;

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardHeader
        title="AI Audit Metadata"
        titleTypographyProps={{ variant: "subtitle2" }}
      />
      <CardContent sx={{ pt: 0 }}>
        <Stack spacing={1}>
          {fields.map((f) => (
            <Box key={f.source} display="flex" gap={1}>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ minWidth: 140 }}
              >
                {f.label}:
              </Typography>
              <Typography variant="body2">
                {record[f.source] ? (record[f.source] as string) : "N/A"}
              </Typography>
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

// ---- Message Content Card ----

const MessageContentCard = () => {
  const { record, isLoading } = useShowContext();

  if (isLoading || !record) return null;

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardHeader
        title="Message Content"
        titleTypographyProps={{ variant: "subtitle2" }}
      />
      <CardContent sx={{ pt: 0 }}>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
            Subject:
          </Typography>
          <MuiTextField
            value={(record.subject as string) ?? ""}
            fullWidth
            size="small"
            slotProps={{ input: { readOnly: true } }}
            variant="outlined"
          />
        </Box>
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
            Body:
          </Typography>
          <MuiTextField
            value={(record.body as string) ?? ""}
            fullWidth
            multiline
            minRows={8}
            maxRows={20}
            slotProps={{ input: { readOnly: true } }}
            variant="outlined"
          />
        </Box>
      </CardContent>
    </Card>
  );
};

// ---- Show Actions ----

const ShowActions = () => (
  <TopToolbar>
    <ListButton />
    <EditButton />
  </TopToolbar>
);

// ---- Main Export ----

export const MessageDraftShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <WorkflowPanel />
      <MessageContentCard />
      <AiAuditCard />
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
      <TextField source="tone" />
      <TextField source="review_notes" emptyText="N/A" />
      <DateField source="approved_at" showTime emptyText="N/A" />
      <DateField source="sent_at" showTime emptyText="N/A" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
