import { useEffect, useState } from "react";
import { useNotify } from "react-admin";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { API_BASE_URL } from "../../config";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SourceCatalogEntry {
  provider: string;
  label: string;
  country: string;
  language: string;
  source_kind: string;
  interaction_mode: string;
  description: string;
  usage_guide: string;
  search_url: string;
  profile_url: string;
  is_manual_source: boolean;
  supports_real_api: boolean;
  requires_credentials: boolean;
  human_review_required: boolean;
  importable: boolean;
  scraping_allowed: boolean;
  external_message_allowed: boolean;
  recommended_for: string;
  notes: string;
}

/* ------------------------------------------------------------------ */
/*  Safety badge config                                                */
/* ------------------------------------------------------------------ */

interface Badge {
  label: string;
  color: "warning" | "default" | "error" | "info";
  title: string;
}

function buildBadges(entry: SourceCatalogEntry): Badge[] {
  const badges: Badge[] = [];

  if (entry.is_manual_source) {
    badges.push({
      label: "Manual source",
      color: "warning",
      title: "Human-driven source, no automation possible",
    });
  }
  if (!entry.supports_real_api) {
    badges.push({
      label: "No real API",
      color: "default",
      title: "No API connector exists for this platform",
    });
  }
  if (!entry.importable) {
    badges.push({
      label: "Not importable",
      color: "error",
      title: "Entries cannot be imported into SORIA",
    });
  }
  if (!entry.scraping_allowed) {
    badges.push({
      label: "No scraping",
      color: "default",
      title: "Scraping is disabled for this platform",
    });
  }
  if (entry.human_review_required) {
    badges.push({
      label: "Human review required",
      color: "info",
      title: "Human oversight is mandatory before any action",
    });
  }

  return badges;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export const SourceCatalog = () => {
  const notify = useNotify();

  const [entries, setEntries] = useState<SourceCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `${API_BASE_URL}/external-sources/source-catalog`,
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
          throw new Error(detail);
        }
        const data: SourceCatalogEntry[] = await res.json();
        if (!cancelled) setEntries(data);
      } catch (e: unknown) {
        if (!cancelled) {
          const message =
            e instanceof Error ? e.message : "Failed to load source catalog";
          setError(message);
          notify(message, { type: "error" });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [notify]);

  /* ---- Loading state ------------------------------------------------ */
  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          French Freelance Source Catalog
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading source catalog...
          </Typography>
        </Box>
      </Box>
    );
  }

  /* ---- Error state -------------------------------------------------- */
  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          French Freelance Source Catalog
        </Typography>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </Box>
    );
  }

  /* ---- Empty state -------------------------------------------------- */
  if (entries.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          French Freelance Source Catalog
        </Typography>
        <Alert severity="info">
          No catalog entries available. The source catalog may not be loaded.
        </Alert>
      </Box>
    );
  }

  /* ---- Catalog entries ---------------------------------------------- */
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        French Freelance Source Catalog
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Reference directory of French freelance platforms. These are
        informational entries only — they cannot be searched, imported, scraped,
        or messaged from within SORIA. All entries require human review.
      </Typography>

      <Stack spacing={2}>
        {entries.map((entry) => {
          const badges = buildBadges(entry);

          return (
            <Card key={entry.provider} variant="outlined">
              <CardContent>
                <Stack spacing={1.5}>
                  {/* Header */}
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="flex-start"
                    flexWrap="wrap"
                    useFlexGap
                  >
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {entry.label}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {entry.provider}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      <Chip
                        label={entry.country}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={entry.language}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={entry.source_kind}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                    </Stack>
                  </Stack>

                  {/* Safety badges */}
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    {badges.map((badge) => (
                      <Chip
                        key={badge.label}
                        label={badge.label}
                        size="small"
                        color={badge.color}
                        variant="outlined"
                        title={badge.title}
                      />
                    ))}
                  </Stack>

                  <Divider />

                  {/* Description */}
                  <Typography variant="body2">{entry.description}</Typography>

                  {/* Interaction mode */}
                  <Typography variant="body2">
                    <strong>Interaction mode:</strong> {entry.interaction_mode}
                  </Typography>

                  {/* Usage guide */}
                  <Typography variant="body2">
                    <strong>Usage guide:</strong> {entry.usage_guide}
                  </Typography>

                  {/* Recommended for */}
                  <Typography variant="body2">
                    <strong>Recommended for:</strong> {entry.recommended_for}
                  </Typography>

                  {/* Notes */}
                  {entry.notes && (
                    <Typography variant="body2" color="text.secondary">
                      <strong>Notes:</strong> {entry.notes}
                    </Typography>
                  )}

                  {/* External links */}
                  <Stack direction="row" spacing={1}>
                    <Button
                      variant="outlined"
                      size="small"
                      href={entry.search_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon />}
                    >
                      Open search URL
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      href={entry.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon />}
                    >
                      Open profile URL
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      {/* Footer disclaimer */}
      <Alert severity="info" sx={{ mt: 3 }}>
        This catalog is for reference only. No external API calls are made by
        SORIA for these platforms. All sourcing must be done manually through
        the provided external links.
      </Alert>
    </Box>
  );
};
