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
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField as MuiTextField,
  Typography,
} from "@mui/material";
import { API_BASE_URL } from "../../config";

const OpportunityActions = () => {
  const { record, isLoading } = useShowContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [aiPreviewOpen, setAiPreviewOpen] = useState(false);
  const [aiPreviewData, setAiPreviewData] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [aiPreviewLoading, setAiPreviewLoading] = useState(false);

  if (isLoading || !record) return null;

  const handleEnrich = async () => {
    setLoading("enrich");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/enrich`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("Opportunity enriched successfully", { type: "success" });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleMatchAssets = async () => {
    setLoading("match");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/match-assets`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("Offer/resources matched successfully", { type: "success" });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleScore = async () => {
    setLoading("score");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/score`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("Opportunity scored successfully", { type: "success" });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleGenerateDraft = async () => {
    setLoading("draft");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/generate-draft`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("Draft generated or existing active draft reused", {
        type: "success",
      });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleRegenerateDraft = async () => {
    setLoading("regenerate");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/regenerate-draft`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("New draft generated (previous active draft archived)", {
        type: "success",
      });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleOpenPreview = async () => {
    setPreviewLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/openproject-preview`,
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
      const data = await res.json();
      setPreviewData(data);
      setPreviewOpen(true);
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
  };

  const handleCopySubject = async () => {
    if (!previewData?.subject) return;
    try {
      await navigator.clipboard.writeText(String(previewData.subject));
      notify("Subject copied to clipboard", { type: "success" });
    } catch {
      notify("Failed to copy subject", { type: "error" });
    }
  };

  const handleCopyDescription = async () => {
    if (!previewData?.description) return;
    try {
      await navigator.clipboard.writeText(String(previewData.description));
      notify("Description copied to clipboard", { type: "success" });
    } catch {
      notify("Failed to copy description", { type: "error" });
    }
  };

  const handleAiPreview = async () => {
    setAiPreviewLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/ai-draft-preview`,
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
      const data = await res.json();
      setAiPreviewData(data);
      setAiPreviewOpen(true);
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setAiPreviewLoading(false);
    }
  };

  const handleCloseAiPreview = () => {
    setAiPreviewOpen(false);
  };

  const handleCopyAiSubject = async () => {
    if (!aiPreviewData?.subject) return;
    try {
      await navigator.clipboard.writeText(String(aiPreviewData.subject));
      notify("Subject copied to clipboard", { type: "success" });
    } catch {
      notify("Failed to copy subject", { type: "error" });
    }
  };

  const handleCopyAiBody = async () => {
    if (!aiPreviewData?.body) return;
    try {
      await navigator.clipboard.writeText(String(aiPreviewData.body));
      notify("Body copied to clipboard", { type: "success" });
    } catch {
      notify("Failed to copy body", { type: "error" });
    }
  };

  const handleGenerateAiDraft = async () => {
    setLoading("ai-draft");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/generate-ai-draft`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("AI draft generated or existing active AI draft reused", {
        type: "success",
      });
      refresh();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Request failed", {
        type: "error",
      });
    } finally {
      setLoading(null);
    }
  };

  const handleRegenerateAiDraft = async () => {
    setLoading("regenerate-ai");
    try {
      const res = await fetch(
        `${API_BASE_URL}/opportunities/${record.id}/regenerate-ai-draft`,
        { method: "POST", headers: { "Content-Type": "application/json" } },
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
      notify("New AI draft generated (previous active AI draft archived)", {
        type: "success",
      });
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
    <>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button
          variant="contained"
          color="info"
          onClick={handleEnrich}
          disabled={loading !== null}
        >
          {loading === "enrich" ? "Enriching..." : "Enrich opportunity"}
        </Button>
        <Button
          variant="contained"
          color="success"
          onClick={handleMatchAssets}
          disabled={loading !== null}
        >
          {loading === "match" ? "Matching..." : "Match offer/resources"}
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleScore}
          disabled={loading !== null}
        >
          {loading === "score" ? "Scoring..." : "Score opportunity"}
        </Button>
        <Button
          variant="contained"
          color="secondary"
          onClick={handleGenerateDraft}
          disabled={loading !== null}
        >
          {loading === "draft" ? "Generating..." : "Generate draft"}
        </Button>
        <Button
          variant="outlined"
          color="warning"
          onClick={handleRegenerateDraft}
          disabled={loading !== null}
        >
          {loading === "regenerate" ? "Regenerating..." : "Regenerate draft"}
        </Button>
        <Button
          variant="contained"
          color="info"
          onClick={handleOpenPreview}
          disabled={loading !== null || previewLoading}
        >
          {previewLoading ? "Loading..." : "OpenProject preview"}
        </Button>
        <Button
          variant="contained"
          color="secondary"
          onClick={handleAiPreview}
          disabled={loading !== null || aiPreviewLoading}
        >
          {aiPreviewLoading ? "Loading..." : "AI draft preview"}
        </Button>
        <Button
          variant="contained"
          color="success"
          onClick={handleGenerateAiDraft}
          disabled={loading !== null}
        >
          {loading === "ai-draft" ? "Generating..." : "Generate AI draft"}
        </Button>
        <Button
          variant="outlined"
          color="warning"
          onClick={handleRegenerateAiDraft}
          disabled={loading !== null}
        >
          {loading === "regenerate-ai"
            ? "Regenerating..."
            : "Regenerate AI draft"}
        </Button>
      </Stack>
      <Dialog
        open={previewOpen}
        onClose={handleClosePreview}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>OpenProject Work Package Preview</DialogTitle>
        <DialogContent dividers>
          {previewData && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                Type: {String(previewData.suggested_type ?? "")}
                {" | "}Status: {String(previewData.suggested_status ?? "")}
                {" | "}Priority: {String(previewData.suggested_priority ?? "")}
              </Typography>
              <MuiTextField
                label="Subject"
                value={String(previewData.subject ?? "")}
                fullWidth
                margin="normal"
                size="small"
                InputProps={{ readOnly: true }}
              />
              <MuiTextField
                label="Description (Markdown)"
                value={String(previewData.description ?? "")}
                fullWidth
                multiline
                minRows={15}
                maxRows={30}
                margin="normal"
                size="small"
                InputProps={{ readOnly: true }}
                variant="outlined"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCopySubject} color="primary">
            Copy subject
          </Button>
          <Button onClick={handleCopyDescription} color="primary">
            Copy description
          </Button>
          <Button onClick={handleClosePreview}>Close</Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={aiPreviewOpen}
        onClose={handleCloseAiPreview}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>AI Draft Preview</DialogTitle>
        <DialogContent dividers>
          {aiPreviewData && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                Provider: {String(aiPreviewData.provider ?? "")}
                {" | "}Model: {String(aiPreviewData.model_name ?? "")}
                {" | "}Prompt: {String(aiPreviewData.prompt_version ?? "")}
              </Typography>
              <MuiTextField
                label="Subject"
                value={String(aiPreviewData.subject ?? "")}
                fullWidth
                margin="normal"
                size="small"
                InputProps={{ readOnly: true }}
              />
              <MuiTextField
                label="Body"
                value={String(aiPreviewData.body ?? "")}
                fullWidth
                multiline
                minRows={10}
                maxRows={25}
                margin="normal"
                size="small"
                InputProps={{ readOnly: true }}
                variant="outlined"
              />
              <MuiTextField
                label="Safety note"
                value={String(aiPreviewData.safety_note ?? "")}
                fullWidth
                margin="normal"
                size="small"
                InputProps={{ readOnly: true }}
                variant="outlined"
                color="warning"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCopyAiSubject} color="primary">
            Copy subject
          </Button>
          <Button onClick={handleCopyAiBody} color="primary">
            Copy body
          </Button>
          <Button onClick={handleCloseAiPreview}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

const ShowActions = () => (
  <TopToolbar>
    <ListButton />
    <EditButton />
  </TopToolbar>
);

export const OpportunityShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <OpportunityActions />
      <TextField source="id" />
      <ReferenceField source="company_id" reference="companies" link="show" />
      <ReferenceField
        source="contact_id"
        reference="contacts"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="offer_id"
        reference="offers"
        link="show"
        emptyText="N/A"
      />
      <ReferenceField
        source="academy_resource_id"
        reference="academy-resources"
        link="show"
        emptyText="N/A"
      />
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
      <TextField source="openproject_work_package_id" emptyText="N/A" />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
