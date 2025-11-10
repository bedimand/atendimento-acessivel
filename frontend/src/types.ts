export type MessageOrigin = "user" | "bot";

export type Message = {
  id: number;
  origin: MessageOrigin;
  content: string;
  created_at: string;
};
