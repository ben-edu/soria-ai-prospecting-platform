import { Alert } from "@mui/material";
import {
  Button,
  DateField,
  ListButton,
  Show,
  SimpleShowLayout,
  TextField,
  TopToolbar,
  useRecordContext,
} from "react-admin";
import { useNavigate } from "react-router-dom";

const ShowActions = () => (
  <TopToolbar>
    <ListButton />
  </TopToolbar>
);

const JsonField = ({ source }: { source: string }) => {
  const record = useRecordContext();
  if (!record) return null;
  const value = record[source];
  if (!value) return <span>N/A</span>;
  try {
    return (
      <pre
        style={{
          background: "#f5f5f5",
          padding: "1em",
          borderRadius: "4px",
          overflow: "auto",
          maxHeight: "400px",
          fontSize: "0.85em",
          lineHeight: "1.4",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  } catch {
    return <span>{String(value)}</span>;
  }
};

const LinkedEntityButton = ({
  id,
  label,
  resource,
}: {
  id: string | null | undefined;
  label: string;
  resource: string;
}) => {
  const navigate = useNavigate();
  if (!id) return null;
  return (
    <Button
      label={label}
      onClick={() => navigate(`/${resource}/${id}/show`)}
      sx={{ mr: 1 }}
    />
  );
};

const LinkedEntities = () => {
  const record = useRecordContext();
  if (!record) return null;

  const hasCompany = !!record.linked_company_id;
  const hasOpportunity = !!record.linked_opportunity_id;

  if (!hasCompany && !hasOpportunity) {
    return <span>None — no linked entities</span>;
  }

  return (
    <div style={{ display: "flex", gap: "0.5em", alignItems: "center" }}>
      {hasCompany && (
        <LinkedEntityButton
          id={record.linked_company_id}
          label="View linked company"
          resource="companies"
        />
      )}
      {hasOpportunity && (
        <LinkedEntityButton
          id={record.linked_opportunity_id}
          label="View linked opportunity"
          resource="opportunities"
        />
      )}
    </div>
  );
};

const ReadOnlyAlert = () => (
  <Alert severity="info" sx={{ mx: "1em", mb: "1em" }}>
    SourceRecords are read-only provenance records. They document external
    imports and provider metadata. They do not trigger outreach, drafts,
    follow-ups, or compliance events.
  </Alert>
);

export const SourceRecordShow = () => (
  <Show actions={<ShowActions />}>
    <SimpleShowLayout>
      <ReadOnlyAlert />
      <TextField source="id" />
      <TextField source="source_type" />
      <TextField source="source_name" emptyText="N/A" />
      <TextField source="source_url" emptyText="N/A" />
      <TextField source="external_id" emptyText="N/A" />
      <JsonField source="raw_payload" />
      <DateField source="imported_at" showTime />
      <TextField source="processed" />
      <TextField source="processing_notes" emptyText="N/A" />
      <TextField source="linked_company_id" emptyText="N/A" />
      <TextField source="linked_opportunity_id" emptyText="N/A" />
      <LinkedEntities />
      <DateField source="created_at" showTime />
      <DateField source="updated_at" showTime />
    </SimpleShowLayout>
  </Show>
);
