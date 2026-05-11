/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        huawei: {
          red: "var(--hw-red)",
          "red-bright": "var(--hw-red-bright)",
          "red-light": "var(--hw-red-light)",
          "red-glow": "var(--hw-red-glow)",
          gray: {
            50: "var(--hw-gray-50)",
            100: "var(--hw-gray-100)",
            200: "var(--hw-gray-200)",
            300: "var(--hw-gray-300)",
            400: "var(--hw-gray-400)",
            500: "var(--hw-gray-500)",
            600: "var(--hw-gray-600)",
            700: "var(--hw-gray-700)",
            800: "var(--hw-gray-800)",
            900: "var(--hw-gray-900)",
          },
        },
        surface: "var(--surface)",
        "surface-hover": "var(--surface-hover)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-tertiary": "var(--text-tertiary)",
        "border-light": "var(--border-light)",
        "border-medium": "var(--border-medium)",
        "bg-base": "var(--bg-base)",
        "bg-secondary": "var(--bg-secondary)",
        "bg-tertiary": "var(--bg-tertiary)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
