import { useState, useEffect } from "react";
import { useNotify } from "react-admin";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  Stack,
  TextField as MuiTextField,
  Typography,
} from "@mui/material";
import { API_BASE_URL } from "../../config";

/* ------------------------------------------------------------------ */
/*  TypeScript interfaces                                              */
/* ------------------------------------------------------------------ */

interface ExternalSourceProviderInfo {
  provider: string;
  label: string;
  country: string | null;
  source_kind: string;
  is_enabled: boolean;
  is_mock: boolean;
  requires_credentials: boolean;
  description: string;
}

interface ExternalSourceDiagnosticsResponse {
  providers: ExternalSourceProviderInfo[];
  enabled_providers: string[];
  mock_only: boolean;
  message: string;
}

interface ExternalOpportunityCandidate {
  provider: string;
  external_id: string;
  source_kind: string;
  title: string;
  company_name: string | null;
  description: string | null;
  location: string | null;
  country: string | null;
  language: string;
  source_url: string | null;
  source_published_at: string | null;
  contract_type: string | null;
  remote_type: string | null;
  budget_min: number | null;
  budget_max: number | null;
  budget_currency: string | null;
  tags: string[];
  raw_payload: Record<string, unknown>;
}

interface ExternalOpportunitySearchResponse {
  provider: string | null;
  query: string;
  location: string | null;
  total: number;
  items: ExternalOpportunityCandidate[];
}

interface ImportExternalCandidateResponse {
  source_record: Record<string, unknown>;
  company: Record<string, unknown>;
  opportunity: Record<string, unknown>;
  created_source_record: boolean;
  created_company: boolean;
  created_opportunity: boolean;
  duplicate_detected: boolean;
  message: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function candidateKey(candidate: ExternalOpportunityCandidate): string {
  return `${candidate.provider}::${candidate.external_id}`;
}

function formatBudget(candidate: ExternalOpportunityCandidate): string | null {
  const { budget_min, budget_max, budget_currency } = candidate;
  if (budget_min === null && budget_max === null) return null;
  const parts: string[] = [];
  if (budget_min !== null) parts.push(budget_min.toLocaleString());
  if (budget_max !== null) parts.push(budget_max.toLocaleString());
  const currency = budget_currency ?? "";
  return `${parts.join(" - ")}${currency ? ` (${currency})` : ""}`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export const ExternalSourceSearch = () => {
  const navigate = useNavigate();
  const notify = useNotify();

  /* Diagnostics ----------------------------------------------------- */
  const [diagnostics, setDiagnostics] =
    useState<ExternalSourceDiagnosticsResponse | null>(null);
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(true);

  /* Search form ----------------------------------------------------- */
  const [selectedProviders, setSelectedProviders] = useState<string[]>([
    "france_travail",
    "adzuna_uk",
    "freelancer",
  ]);
  const [query, setQuery] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [limit, setLimit] = useState(5);

  /* Search results -------------------------------------------------- */
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<
    ExternalOpportunityCandidate[] | null
  >(null);
  const [searchPerformed, setSearchPerformed] = useState(false);

  /* Import state (keyed per candidate) ------------------------------ */
  const [importLoading, setImportLoading] = useState<Record<string, boolean>>(
    {},
  );
  const [importResults, setImportResults] = useState<
    Record<string, ImportExternalCandidateResponse>
  >({});

  /* ---- Load diagnostics on mount ---------------------------------- */
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/external-sources/providers`);
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
        const data: ExternalSourceDiagnosticsResponse = await res.json();
        if (!cancelled) setDiagnostics(data);
      } catch (e: unknown) {
        if (!cancelled) {
          notify(
            e instanceof Error
              ? e.message
              : "Failed to load provider diagnostics",
            { type: "error" },
          );
        }
      } finally {
        if (!cancelled) setLoadingDiagnostics(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [notify]);

  /* ---- Handlers --------------------------------------------------- */
  const handleProviderToggle = (provider: string) => {
    setSelectedProviders((prev) =>
      prev.includes(provider)
        ? prev.filter((p) => p !== provider)
        : [...prev, provider],
    );
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      notify("Search query cannot be blank. Please enter a search term.", {
        type: "warning",
      });
      return;
    }
    if (selectedProviders.length === 0) {
      notify("Please select at least one provider.", { type: "warning" });
      return;
    }

    setSearching(true);
    setSearchPerformed(true);
    setImportResults({});

    const params = new URLSearchParams({
      providers: selectedProviders.join(","),
      query: query.trim(),
      limit: String(limit),
    });
    if (locationFilter.trim()) {
      params.set("location", locationFilter.trim());
    }

    try {
      const res = await fetch(
        `${API_BASE_URL}/external-sources/search?${params.toString()}`,
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
        setSearchResults([]);
        return;
      }
      const data: ExternalOpportunitySearchResponse = await res.json();
      setSearchResults(data.items);
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Search request failed", {
        type: "error",
      });
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleImport = async (candidate: ExternalOpportunityCandidate) => {
    const key = candidateKey(candidate);
    setImportLoading((prev) => ({ ...prev, [key]: true }));

    try {
      const res = await fetch(
        `${API_BASE_URL}/external-sources/import-candidate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(candidate),
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
      const result: ImportExternalCandidateResponse = await res.json();
      setImportResults((prev) => ({ ...prev, [key]: result }));

      if (result.duplicate_detected) {
        notify(`Duplicate detected — ${result.message}`, {
          type: "warning",
        });
      } else {
        const created = [
          result.created_source_record ? "SourceRecord" : null,
          result.created_company ? "Company" : null,
          result.created_opportunity ? "Opportunity" : null,
        ]
          .filter(Boolean)
          .join(", ");
        notify(`Imported successfully (created: ${created})`, {
          type: "success",
        });
      }
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Import request failed", {
        type: "error",
      });
    } finally {
      setImportLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  /* ---- Derived values --------------------------------------------- */
  const providerOptions = diagnostics?.providers ?? [];

  /* ---- Render ----------------------------------------------------- */
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        External Source Search & Import
      </Typography>

      {/* Loading diagnostics */}
      {loadingDiagnostics && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading provider diagnostics...
          </Typography>
        </Box>
      )}

      {/* Mock-only banner */}
      {diagnostics?.mock_only && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {diagnostics.message}
        </Alert>
      )}

      {/* Provider diagnostics summary */}
      {diagnostics && providerOptions.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              Available Providers
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {providerOptions.map((p) => (
                <Chip
                  key={p.provider}
                  label={`${p.label} (${p.provider})`}
                  variant="outlined"
                  color={p.is_mock ? "default" : "primary"}
                  size="small"
                  title={`${p.description} | ${p.country ?? "N/A"} | ${p.source_kind}`}
                />
              ))}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              All providers are mock-only in Phase 9A/9B. No real external API
              calls are made. Credentials are not required.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Search form */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Search External Sources
          </Typography>
          <Stack spacing={2}>
            {/* Provider checkboxes */}
            <Box>
              <Typography variant="body2" fontWeight="medium" sx={{ mb: 0.5 }}>
                Providers
              </Typography>
              {providerOptions.length > 0 ? (
                <FormGroup row>
                  {providerOptions.map((p) => (
                    <FormControlLabel
                      key={p.provider}
                      control={
                        <Checkbox
                          checked={selectedProviders.includes(p.provider)}
                          onChange={() => handleProviderToggle(p.provider)}
                          size="small"
                        />
                      }
                      label={
                        <Typography variant="body2">
                          {p.label} ({p.provider})
                        </Typography>
                      }
                    />
                  ))}
                </FormGroup>
              ) : (
                !loadingDiagnostics && (
                  <FormHelperText error>
                    No providers available. Ensure the backend is running.
                  </FormHelperText>
                )
              )}
              {selectedProviders.length === 0 && (
                <FormHelperText error>
                  Select at least one provider
                </FormHelperText>
              )}
            </Box>

            {/* Query, Location, Limit */}
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={2}
              alignItems="flex-start"
            >
              <MuiTextField
                label="Query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. devops, cloud engineer, data scientist"
                fullWidth
                size="small"
                required
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleSearch();
                }}
              />
              <MuiTextField
                label="Location (optional)"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
                placeholder="e.g. Paris, London"
                fullWidth
                size="small"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleSearch();
                }}
              />
              <MuiTextField
                label="Limit"
                type="number"
                value={limit}
                onChange={(e) => {
                  const raw = e.target.value;
                  if (raw === "") {
                    setLimit(1);
                    return;
                  }
                  const val = parseInt(raw, 10);
                  if (!isNaN(val)) {
                    setLimit(Math.max(1, Math.min(50, val)));
                  }
                }}
                inputProps={{ min: 1, max: 50 }}
                size="small"
                sx={{ minWidth: 100, maxWidth: 120 }}
              />
            </Stack>

            {/* Search button */}
            <Box>
              <Button
                variant="contained"
                onClick={() => void handleSearch()}
                disabled={searching}
              >
                {searching ? "Searching..." : "Search"}
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Searching indicator */}
      {searching && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Searching external sources...
          </Typography>
        </Box>
      )}

      {/* No results */}
      {searchPerformed &&
        !searching &&
        searchResults !== null &&
        searchResults.length === 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            No results found. Try a different search query or provider
            selection.
          </Alert>
        )}

      {/* Results */}
      {searchResults !== null && searchResults.length > 0 && (
        <>
          <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2 }}>
            Results ({searchResults.length})
          </Typography>
          <Stack spacing={2}>
            {searchResults.map((candidate) => {
              const key = candidateKey(candidate);
              const isImporting = importLoading[key] ?? false;
              const importResult = importResults[key];
              const budgetLabel = formatBudget(candidate);

              return (
                <Card key={key} variant="outlined">
                  <CardContent>
                    <Stack spacing={1.5}>
                      {/* Header */}
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="flex-start"
                      >
                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {candidate.title}
                          </Typography>
                          {candidate.company_name && (
                            <Typography variant="body2" color="text.secondary">
                              {candidate.company_name}
                            </Typography>
                          )}
                        </Box>
                        <Stack direction="row" spacing={0.5}>
                          <Chip
                            label={candidate.provider}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                          <Chip
                            label={candidate.source_kind}
                            size="small"
                            variant="outlined"
                          />
                        </Stack>
                      </Stack>

                      <Divider />

                      {/* Details */}
                      <Stack
                        direction="row"
                        spacing={2}
                        flexWrap="wrap"
                        useFlexGap
                      >
                        {candidate.location && (
                          <Typography variant="body2">
                            <strong>Location:</strong> {candidate.location}
                          </Typography>
                        )}
                        {candidate.country && (
                          <Typography variant="body2">
                            <strong>Country:</strong> {candidate.country}
                          </Typography>
                        )}
                        {candidate.language && (
                          <Typography variant="body2">
                            <strong>Language:</strong> {candidate.language}
                          </Typography>
                        )}
                        {candidate.contract_type && (
                          <Typography variant="body2">
                            <strong>Contract:</strong> {candidate.contract_type}
                          </Typography>
                        )}
                        {candidate.remote_type && (
                          <Typography variant="body2">
                            <strong>Remote:</strong> {candidate.remote_type}
                          </Typography>
                        )}
                      </Stack>

                      {/* Budget */}
                      {budgetLabel && (
                        <Typography variant="body2">
                          <strong>Budget:</strong> {budgetLabel}
                        </Typography>
                      )}

                      {/* Tags */}
                      {candidate.tags.length > 0 && (
                        <Stack
                          direction="row"
                          spacing={0.5}
                          flexWrap="wrap"
                          useFlexGap
                        >
                          {candidate.tags.map((tag) => (
                            <Chip
                              key={tag}
                              label={tag}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Stack>
                      )}

                      {/* Source URL */}
                      {candidate.source_url && (
                        <Typography variant="body2">
                          <strong>Source:</strong>{" "}
                          <a
                            href={candidate.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {candidate.source_url}
                          </a>
                        </Typography>
                      )}

                      {/* Import result */}
                      {importResult && (
                        <>
                          <Divider />
                          {importResult.duplicate_detected ? (
                            <Alert severity="warning" sx={{ mt: 1 }}>
                              {importResult.message}
                            </Alert>
                          ) : (
                            <Alert severity="success" sx={{ mt: 1 }}>
                              {importResult.message}
                            </Alert>
                          )}
                          <Stack direction="row" spacing={1}>
                            {importResult.company &&
                              "id" in importResult.company && (
                                <Button
                                  size="small"
                                  variant="outlined"
                                  onClick={() =>
                                    navigate(
                                      `/companies/${String(importResult.company.id)}/show`,
                                    )
                                  }
                                >
                                  View company
                                </Button>
                              )}
                            {importResult.opportunity &&
                              "id" in importResult.opportunity && (
                                <Button
                                  size="small"
                                  variant="contained"
                                  onClick={() =>
                                    navigate(
                                      `/opportunities/${String(importResult.opportunity.id)}/show`,
                                    )
                                  }
                                >
                                  View opportunity
                                </Button>
                              )}
                          </Stack>
                        </>
                      )}

                      {/* Import button (hidden after import) */}
                      {!importResult && (
                        <Box>
                          <Button
                            variant="contained"
                            color="primary"
                            size="small"
                            onClick={() => void handleImport(candidate)}
                            disabled={isImporting}
                          >
                            {isImporting ? "Importing..." : "Import"}
                          </Button>
                        </Box>
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              );
            })}
          </Stack>
        </>
      )}

      {/* Initial empty state */}
      {!searchPerformed && searchResults === null && !searching && (
        <Typography variant="body2" color="text.secondary">
          Use the search form above to find external candidates. All results
          come from mock providers in Phase 9A/9B — no real external API calls
          are made.
        </Typography>
      )}
    </Box>
  );
};
