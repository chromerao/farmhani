export type View = "dashboard" | "add" | "detail" | "chat";

export type Plant = {
  id: string;
  name: string;
  species?: string | null;
  location?: string | null;
  sunlight?: string | null;
  createdAt: string;
  imageUrl?: string;
  healthScore?: number;
  moisture?: string;
  nextTask?: string;
};

export type CareLog = {
  id: string;
  plantId: string;
  wateredAt?: string | null;
  leafCondition?: string | null;
  soilCondition?: string | null;
  memo?: string | null;
  createdAt: string;
};

export type PlantPhoto = {
  id: string;
  plantId: string;
  storagePath: string;
  capturedAt?: string | null;
  note?: string | null;
  createdAt: string;
};

export type PlantCatalogItem = {
  id: string;
  name: string;
  species: string;
  familyName?: string | null;
  description?: string | null;
};

export type UploadSignedUrlResponse = {
  signedUrl: string;
  storagePath: string;
};

export type PlantCareChatResponse = {
  summary: string;
  possibleCauses: string[];
  todayActions: string[];
  observationChecklist: string[];
  citations: {
    sourceId: string;
    title: string;
    url?: string;
    publisher?: string;
    excerpt?: string;
    section?: string;
  }[];
  safetyNotice?: string;
  sessionId?: string;
  messageId?: string;
};

export type ChatSession = {
  id: string;
  userId: string;
  plantId?: string | null;
  createdAt: string;
};

export type ChatMessage = {
  id: string;
  sessionId: string;
  sender: "user" | "assistant";
  content: string;
  citations?: PlantCareChatResponse["citations"];
  createdAt: string;
};
