import { API_BASE_URL } from "./config";

const resourceUrl = (resource: string, id?: string | number): string => {
  const base = `${API_BASE_URL}/${resource}`;
  return id != null ? `${base}/${id}` : base;
};

const parseErrorDetail = (body: string): string => {
  try {
    const parsed = JSON.parse(body);
    if (parsed.detail) {
      if (Array.isArray(parsed.detail)) {
        return parsed.detail.map((e: { msg: string }) => e.msg).join("; ");
      }
      return String(parsed.detail);
    }
  } catch {
    // not JSON — return raw body
  }
  return body;
};

const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(parseErrorDetail(body));
  }
  return response.json();
};

const filtersToParams = (
  filter: Record<string, string | undefined>,
  url: URL,
): void => {
  for (const [key, value] of Object.entries(filter)) {
    if (value != null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
};

export const dataProvider = {
  getList: async (
    resource: string,
    params: {
      pagination?: { page?: number; perPage?: number };
      sort?: { field?: string; order?: string };
      filter?: Record<string, string>;
    },
  ) => {
    const { page = 1, perPage = 50 } = params.pagination ?? {};
    const url = new URL(resourceUrl(resource));
    url.searchParams.set("skip", String((page - 1) * perPage));
    url.searchParams.set("limit", String(perPage));
    filtersToParams(params.filter ?? {}, url);

    const json = await handleResponse(await fetch(url.toString()));
    return { data: json.items, total: json.total };
  },

  getOne: async (_resource: string, params: { id: string | number }) => {
    const json = await handleResponse(
      await fetch(resourceUrl(_resource, params.id)),
    );
    return { data: json };
  },

  getMany: async (_resource: string, params: { ids: (string | number)[] }) => {
    const results = await Promise.all(
      params.ids.map((id) =>
        fetch(resourceUrl(_resource, id)).then((r) => r.json()),
      ),
    );
    return { data: results };
  },

  getManyReference: async (
    resource: string,
    params: {
      target: string;
      id: string | number;
      pagination?: { page?: number; perPage?: number };
      sort?: { field?: string; order?: string };
      filter?: Record<string, string>;
    },
  ) => {
    const { page = 1, perPage = 25 } = params.pagination ?? {};
    const url = new URL(resourceUrl(resource));
    url.searchParams.set("skip", String((page - 1) * perPage));
    url.searchParams.set("limit", String(perPage));
    url.searchParams.set(params.target, String(params.id));
    filtersToParams(params.filter ?? {}, url);

    const json = await handleResponse(await fetch(url.toString()));
    return { data: json.items, total: json.total };
  },

  create: async (
    _resource: string,
    params: { data: Record<string, unknown> },
  ) => {
    const json = await handleResponse(
      await fetch(resourceUrl(_resource), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params.data),
      }),
    );
    return { data: json };
  },

  update: async (
    _resource: string,
    params: { id: string | number; data: Record<string, unknown> },
  ) => {
    const json = await handleResponse(
      await fetch(resourceUrl(_resource, params.id), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params.data),
      }),
    );
    return { data: json };
  },

  delete: async () => {
    throw new Error(
      "Delete is not supported by the backend API for any resource",
    );
  },

  deleteMany: async () => {
    throw new Error(
      "Delete is not supported by the backend API for any resource",
    );
  },
};
