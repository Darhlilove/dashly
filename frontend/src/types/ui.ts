// UI component types

export interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
}
