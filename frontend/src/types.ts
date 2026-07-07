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

export type ChatResponseMode = "expert" | "companion";
export type ChatFeedbackRating = "helpful" | "not_helpful" | "unsafe" | "irrelevant";

export type ChatMemoryMessage = {
  role: "user" | "assistant";
  content: string;
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

export type ChatProgressEvent = {
  step: number;
  total: number;
  node: string;
  label: string;
};

export type ChecklistTask = {
  id: string;
  plantId: string;
  plantName: string;
  taskType: "water" | "observe" | "photo";
  title: string;
  description: string;
  done: boolean;
};

export type WateringReminder = {
  plantId: string;
  name: string;
  species?: string | null;
  lastWateredAt?: string | null;
  daysSinceWatered?: number | null;
  intervalDays: number;
  status: "due" | "upcoming" | "ok" | "unknown";
};

export type ChatModelInfo = {
  chatModel: string;
  visionModel: string;
};

export type ChatSession = {
  id: string;
  userId: string;
  plantId?: string | null;
  title?: string | null;
  createdAt: string;
};

export type ChatFeedbackItem = {
  messageId: string;
  rating: ChatFeedbackRating;
  comment?: string | null;
};

export type SessionFeedbackStats = {
  sessionId: string;
  title?: string | null;
  helpful: number;
  notHelpful: number;
  unsafe: number;
  irrelevant: number;
  total: number;
};

export type ChatMessage = {
  id: string;
  sessionId: string;
  sender: "user" | "assistant";
  content: string;
  citations?: PlantCareChatResponse["citations"];
  createdAt: string;
};
