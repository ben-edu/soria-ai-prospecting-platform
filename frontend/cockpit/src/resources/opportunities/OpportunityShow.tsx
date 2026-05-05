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

const OpportunityActions = () => {
  const { record, isLoading } = useShowContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = useState<string | null>(null);

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

  return (
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
    </Stack>
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
      <TextField source="offer_id" emptyText="N/A" />
      <TextField source="academy_resource_id" emptyText="N/A" />
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
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
