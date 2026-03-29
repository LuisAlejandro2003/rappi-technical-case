import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        rappi: {
          primary: "#FF441F",
          dark: "#1A1A2E",
          light: "#F5F5F5",
        },
      },
    },
  },
  plugins: [],
};

export default config;
