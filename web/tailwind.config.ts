import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./tests/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#171912",
        fog: "#f4f6f1",
        ember: "#b64a35",
        clay: "#59614e",
        moss: "#66784f",
        brass: "#8a7438",
      },
      boxShadow: {
        glow: "0 24px 80px rgba(16, 19, 31, 0.18)",
      },
      letterSpacing: {
        story: "0.18em",
      },
    },
  },
  plugins: [],
};

export default config;
