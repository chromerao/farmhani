import { mockChatResponse, mockPlants } from "./mockData";
import type {
  CareLog,
  ChatMessage,
  ChatSession,
  Plant,
  PlantCareChatResponse,
  PlantCatalogItem,
  PlantPhoto,
  UploadSignedUrlResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";
const SUPABASE_STORAGE_BUCKET = import.meta.env.VITE_SUPABASE_STORAGE_BUCKET || "plant-photos";

const ACCESS_TOKEN_KEY = "farmhani_access_token";
const REFRESH_TOKEN_KEY = "farmhani_refresh_token";
const LOCAL_PLANTS_KEY = "farmhani_local_plants";

type RequestOptions = RequestInit & {
  auth?: boolean;
};

type AuthResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  user?: {
    id: string;
    email?: string;
  };
};

export class AuthRequiredError extends Error {
  constructor(message = "로그인이 필요합니다.") {
    super(message);
    this.name = "AuthRequiredError";
  }
}

export function isAuthRequiredError(error: unknown) {
  return error instanceof AuthRequiredError || (error instanceof Error && error.name === "AuthRequiredError");
}

export function hasSupabaseAuthConfig() {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function hasAuthSession() {
  return Boolean(getAccessToken());
}

export function storagePathToPublicUrl(storagePath?: string | null) {
  if (!storagePath) return undefined;
  if (/^(https?:|blob:|data:)/.test(storagePath)) return storagePath;
  if (!SUPABASE_URL) return undefined;

  const bucketPrefix = `${SUPABASE_STORAGE_BUCKET}/`;
  const cleanPath = storagePath.replace(/^\/+/, "");
  const pathWithoutBucket = cleanPath.startsWith(bucketPrefix) ? cleanPath.slice(bucketPrefix.length) : cleanPath;
  const encodedPath = pathWithoutBucket
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");

  return `${SUPABASE_URL.replace(/\/$/, "")}/storage/v1/object/public/${encodeURIComponent(SUPABASE_STORAGE_BUCKET)}/${encodedPath}`;
}

function saveAuthSession(data: AuthResponse) {
  if (data.access_token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  }
  if (data.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  }
}

export function clearAuthSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function supabaseAuthRequest(path: string, body: unknown): Promise<AuthResponse> {
  if (!hasSupabaseAuthConfig()) {
    throw new Error("Supabase frontend auth env is not configured.");
  }

  const response = await fetch(`${SUPABASE_URL.replace(/\/$/, "")}/auth/v1/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Supabase auth failed: ${response.status}`);
  }

  const data = (await response.json()) as AuthResponse;
  saveAuthSession(data);
  return data;
}

export async function signInWithPassword(email: string, password: string) {
  const data = await supabaseAuthRequest("token?grant_type=password", { email, password });
  if (!data.access_token) {
    throw new AuthRequiredError("로그인 토큰을 받지 못했습니다. 이메일 인증 상태를 확인한 뒤 다시 로그인해 주세요.");
  }
  return data;
}

export async function signUpWithPassword(email: string, password: string) {
  return supabaseAuthRequest("signup", { email, password });
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const bodyIsFormData = options.body instanceof FormData;

  if (!bodyIsFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth !== false) {
    const token = getAccessToken();
    if (!token) {
      throw new AuthRequiredError();
    }
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401 || response.status === 403) {
    throw new AuthRequiredError("세션이 만료되었거나 로그인이 필요합니다.");
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function loadLocalPlants(): Plant[] {
  const stored = localStorage.getItem(LOCAL_PLANTS_KEY);
  if (!stored) return mockPlants;
  try {
    return JSON.parse(stored) as Plant[];
  } catch {
    return mockPlants;
  }
}

function saveLocalPlants(plants: Plant[]) {
  localStorage.setItem(LOCAL_PLANTS_KEY, JSON.stringify(plants));
}

export async function getPlants(): Promise<Plant[]> {
  if (!hasSupabaseAuthConfig()) {
    return loadLocalPlants();
  }
  return request<Plant[]>("/api/v1/plants");
}

export async function getPlant(plantId: string) {
  return request<Plant & { careLogs: CareLog[]; photos: PlantPhoto[] }>(`/api/v1/plants/${plantId}`);
}

export async function updatePlant(
  plantId: string,
  input: Partial<Pick<Plant, "name" | "species" | "location" | "sunlight" | "imageUrl">>
): Promise<Plant> {
  if (!hasSupabaseAuthConfig()) {
    const plants = loadLocalPlants();
    const nextPlants = plants.map((plant) => (plant.id === plantId ? { ...plant, ...input } : plant));
    saveLocalPlants(nextPlants);
    return nextPlants.find((plant) => plant.id === plantId) ?? plants[0];
  }

  return request<Plant>(`/api/v1/plants/${plantId}`, {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export async function createPlant(input: Pick<Plant, "name" | "species" | "location" | "sunlight">): Promise<Plant> {
  if (!hasSupabaseAuthConfig()) {
    const plant: Plant = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      healthScore: 88,
      moisture: "기록 대기",
      nextTask: "첫 관찰 기록 작성",
      ...input
    };
    saveLocalPlants([plant, ...loadLocalPlants()]);
    return plant;
  }

  return request<Plant>("/api/v1/plants", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function createCareLog(
  plantId: string,
  input: Pick<CareLog, "wateredAt" | "leafCondition" | "soilCondition" | "memo">
) {
  return request<CareLog>(`/api/v1/plants/${plantId}/care-logs`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function searchPlantCatalog(q: string, limit = 6): Promise<PlantCatalogItem[]> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  params.set("limit", String(limit));

  try {
    return await request<PlantCatalogItem[]>(`/api/v1/plant-catalog?${params.toString()}`, { auth: false });
  } catch (error) {
    console.warn("[Farmhani] Falling back to local plant catalog:", error);
    const term = q.trim().toLowerCase();
    return [
      { id: "monstera-deliciosa", name: "몬스테라 델리시오사", species: "Monstera deliciosa", familyName: "천남성과" },
      { id: "ficus-elastica", name: "인도고무나무", species: "Ficus elastica", familyName: "뽕나무과" },
      { id: "sansevieria", name: "스투키", species: "Dracaena angolensis", familyName: "아스파라거스과" },
      { id: "spathiphyllum", name: "스파티필럼", species: "Spathiphyllum wallisii", familyName: "천남성과" },
      { id: "rose", name: "장미", species: "Rosa spp.", familyName: "장미과" },
      { id: "strawberry", name: "딸기", species: "Fragaria x ananassa", familyName: "장미과" },
      { id: "potato", name: "감자", species: "Solanum tuberosum", familyName: "가지과" },
      { id: "sweet-potato", name: "고구마", species: "Ipomoea batatas", familyName: "메꽃과" },
      { id: "orchid", name: "난", species: "Orchidaceae", familyName: "난초과" }
    ].filter((item) => !term || item.name.toLowerCase().includes(term) || item.species.toLowerCase().includes(term));
  }
}

export type RagSearchResult = {
  sourceId: string;
  title: string;
  url?: string | null;
  publisher?: string | null;
  excerpt: string;
  score?: number | null;
};

export async function searchRagDocuments(q: string, limit = 5): Promise<RagSearchResult[]> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  params.set("limit", String(limit));
  return request<RagSearchResult[]>(`/api/v1/rag/search?${params.toString()}`, { auth: false });
}

export async function getUploadSignedUrl(file: File): Promise<UploadSignedUrlResponse> {
  return request<UploadSignedUrlResponse>("/api/v1/uploads/signed-url", {
    method: "POST",
    body: JSON.stringify({
      fileName: file.name,
      mimeType: file.type
    })
  });
}

async function uploadFileToSignedUrl(signedUrl: string, file: File) {
  const headers = file.type ? { "Content-Type": file.type } : undefined;
  let lastError: Error | undefined;

  for (const method of ["PUT", "POST"]) {
    try {
      const response = await fetch(signedUrl, {
        method,
        headers,
        body: file
      });
      if (response.ok) return;
      lastError = new Error(`Signed upload failed with ${method}: ${response.status}`);
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  throw lastError ?? new Error("Signed upload failed.");
}

export async function createPlantPhoto(
  plantId: string,
  input: Pick<PlantPhoto, "storagePath" | "capturedAt" | "note">
) {
  return request<PlantPhoto>(`/api/v1/plants/${plantId}/photos`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

async function uploadPlantPhotoViaBackend(plantId: string, file: File, note?: string) {
  const form = new FormData();
  form.append("plantId", plantId);
  form.append("file", file);
  form.append("capturedAt", new Date().toISOString());
  if (note) form.append("note", note);

  return request<PlantPhoto>("/api/v1/uploads/plant-photo", {
    method: "POST",
    body: form
  });
}

export async function uploadPlantPhoto(plantId: string, file: File, note?: string): Promise<PlantPhoto> {
  try {
    const signed = await getUploadSignedUrl(file);
    await uploadFileToSignedUrl(signed.signedUrl, file);
    return await createPlantPhoto(plantId, {
      storagePath: signed.storagePath,
      capturedAt: new Date().toISOString(),
      note
    });
  } catch (error) {
    if (isAuthRequiredError(error)) throw error;
    console.warn("[Farmhani] Signed upload failed, trying backend upload:", error);
    return uploadPlantPhotoViaBackend(plantId, file, note);
  }
}

export async function askPlantCare(
  question: string,
  plantId: string,
  options: { careLogId?: string; photoId?: string; newSession?: boolean } = {}
): Promise<PlantCareChatResponse> {
  if (!hasSupabaseAuthConfig()) {
    return mockChatResponse;
  }

  return request<PlantCareChatResponse>("/api/v1/chat/plant-care", {
    method: "POST",
    body: JSON.stringify({
      plantId,
      careLogId: options.careLogId,
      photoId: options.photoId,
      newSession: options.newSession ?? false,
      question
    })
  });
}

export async function listChatSessions(plantId?: string) {
  const params = new URLSearchParams();
  if (plantId) params.set("plantId", plantId);
  const query = params.toString();
  return request<ChatSession[]>(`/api/v1/chat/sessions${query ? `?${query}` : ""}`);
}

export async function listChatMessages(sessionId: string) {
  return request<ChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
}
