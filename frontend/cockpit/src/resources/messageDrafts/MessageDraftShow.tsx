import { useEffect, useState } from "react";
import {
  Alert,
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
  Link,
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

// ---- Delivery Helper Card ----

interface DeliveryHelperData {
  draft_id: string;
  opportunity_id: string;
  subject: string | null;
  body: string;
  recipient_email: string | null;
  source_url: string | null;
  channel: string;
  recipient_status: string;
  recommended_action: string;
  mailto_url: string | null;
  copy_mode: string;
  warning: string | null;
}

const CHANNEL_LABELS: Record<string, string> = {
  email: "Send via Email",
  application_url: "Send via Platform/Application",
  manual_research: "Manual Contact Research Needed",
};

const CHANNEL_COLORS: Record<string, "success" | "info" | "warning"> = {
  email: "success",
  application_url: "info",
  manual_research: "warning",
};

const DeliveryHelperCard = () => {
  const { record, isLoading } = useShowContext();
  const notify = useNotify();
  const [data, setData] = useState<DeliveryHelperData | null>(null);
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (!record || isLoading) return;

    const fetchHelper = async () => {
      setFetching(true);
      setFetchError(null);
      try {
        const res = await fetch(
          `${API_BASE_URL}/message-drafts/${record.id as string}/delivery-helper`,
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
          setFetchError(detail);
          return;
        }
        const json = (await res.json()) as DeliveryHelperData;
        setData(json);
      } catch (e: unknown) {
        setFetchError(e instanceof Error ? e.message : "Request failed");
      } finally {
        setFetching(false);
      }
    };

    void fetchHelper();
  }, [record, isLoading]);

  const handleCopy = async (text: string | null, label: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      notify(`${label} copied to clipboard`, { type: "success" });
    } catch {
      notify(`Failed to copy ${label.toLowerCase()}`, { type: "error" });
    }
  };

  if (isLoading || !record) return null;

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardHeader
        title="Delivery Helper"
        titleTypographyProps={{ variant: "subtitle2" }}
      />
      <CardContent sx={{ pt: 0 }}>
        {fetching && (
          <Typography variant="body2" color="text.secondary">
            Loading delivery info...
          </Typography>
        )}

        {fetchError && (
          <Alert severity="error" sx={{ py: 0, px: 1.5, mb: 1 }}>
            {fetchError}
          </Alert>
        )}

        {data && (
          <Stack spacing={1.5}>
            {/* Channel Badge */}
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" color="text.secondary">
                Channel:
              </Typography>
              <Chip
                label={CHANNEL_LABELS[data.channel] ?? data.channel}
                color={CHANNEL_COLORS[data.channel] ?? "default"}
                size="small"
              />
            </Box>

            {/* Warning */}
            {data.warning && (
              <Alert severity="warning" sx={{ py: 0, px: 1.5 }}>
                {data.warning}
              </Alert>
            )}

            {/* Recommended Action */}
            <Typography variant="body2" color="text.secondary">
              {data.recommended_action}
            </Typography>

            {/* Recipient Email */}
            {data.recipient_email && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                  Recipient:
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {data.recipient_email}
                </Typography>
              </Box>
            )}

            {/* Source URL */}
            {data.source_url && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                  Source / Application URL:
                </Typography>
                <Link
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="body2"
                >
                  {data.source_url}
                </Link>
              </Box>
            )}

            <Divider />

            {/* Action Buttons */}
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {data.mailto_url && (
                <Button
                  variant="contained"
                  color="success"
                  size="small"
                  href={data.mailto_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open email draft
                </Button>
              )}
              <Button
                variant="outlined"
                size="small"
                onClick={() => handleCopy(data.subject, "Subject")}
              >
                Copy subject
              </Button>
              <Button
                variant="outlined"
                size="small"
                onClick={() => handleCopy(data.body, "Body")}
              >
                Copy body
              </Button>
              {data.source_url && (
                <Button
                  variant="outlined"
                  color="info"
                  size="small"
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open source/apply page
                </Button>
              )}
            </Stack>
          </Stack>
        )}
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
      <DeliveryHelperCard />
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
