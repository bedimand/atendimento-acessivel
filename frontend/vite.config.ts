import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const allowedHosts = [
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
  "ec2-100-27-217-194.compute-1.amazonaws.com",
];

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
  },
  preview: {
    host: "0.0.0.0",
    allowedHosts,
  },
});
