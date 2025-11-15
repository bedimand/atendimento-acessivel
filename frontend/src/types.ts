export type MessageOrigin = "user" | "bot";

export type Message = {
  id: number;
  origin: MessageOrigin;
  content: string;
  created_at: string;
};

export type AvailabilitySlot = {
  date: string;
  slot: string;
  capacity_left: number;
  resources: Record<string, number>;
};

export type UserProfile = {
  fullName: string;
  patientId?: string;
  pronouns?: string;
  disabilities: string[];
  accessibilityNeeds: string[];
  mobilityNotes?: string;
  contactPreference?: string;
  notes?: string;
};

export type Booking = {
  booking_id: number;
  patient_id: number;
  date: string;
  slot: string;
  doctor_name: string;
  warnings: Record<string, unknown>;
  created_at: string;
  specialty: string;
  period: string;
  consultation_type: string;
  urgency: number;
  accessibility: string[];
};
