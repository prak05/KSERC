import type { Config } from "tailwindcss";

const config: Config = {
	darkMode: ["class"],
	content: [
		"./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/components/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/app/**/*.{js,ts,jsx,tsx,mdx}",
	],
	theme: {
		extend: {
			fontFamily: {
				sans: ['Aadhunik', 'var(--font-noto-sans)', 'sans-serif'],
				serif: ['var(--font-eb-garamond)', 'serif'],
				mono: ['var(--font-source-code-pro)', 'monospace'],
			},
			colors: {
				border: "var(--kserc-border)",
				input: "var(--kserc-border)",
				ring: "var(--kserc-navy)",
				background: "var(--kserc-surface)",
				foreground: "var(--kserc-text)",
				kserc: {
					navy: {
						DEFAULT: "var(--kserc-navy)",
						light: "var(--kserc-navy-light)",
						dark: "var(--kserc-navy-dark)",
					},
					gold: {
						DEFAULT: "var(--kserc-gold)",
						light: "var(--kserc-gold-light)",
						dark: "var(--kserc-gold-dark)",
					},
					blue: {
						DEFAULT: "var(--kserc-blue)",
						light: "var(--kserc-blue-light)",
					},
					green: {
						DEFAULT: "var(--kserc-green)",
						light: "var(--kserc-green-light)",
					},
					red: {
						DEFAULT: "var(--kserc-red)",
						light: "var(--kserc-red-light)",
					},
					amber: "var(--kserc-amber)",
					surface: "var(--kserc-surface)",
					border: "var(--kserc-border)",
					text: {
						DEFAULT: "var(--kserc-text)",
						muted: "var(--kserc-text-muted)",
					}
				},
				primary: {
					DEFAULT: "var(--kserc-navy)",
					foreground: "#ffffff",
				},
				secondary: {
					DEFAULT: "var(--kserc-gold)",
					foreground: "#ffffff",
				},
				destructive: {
					DEFAULT: "var(--kserc-red)",
					foreground: "#ffffff",
				},
				muted: {
					DEFAULT: "var(--kserc-text-muted)",
					foreground: "var(--kserc-text)",
				},
				accent: {
					DEFAULT: "var(--kserc-gold)",
					foreground: "var(--kserc-navy)",
				},
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
};
export default config;
