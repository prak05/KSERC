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
				background: 'var(--page)',
				foreground: 'var(--tx)',
				navy: {
					DEFAULT: 'var(--navy)',
					dark: 'var(--navy-d)',
					muted: 'var(--navy-m)',
				},
				gold: {
					DEFAULT: 'var(--gold)',
					light: 'var(--gold2)',
				},
				blue: {
					DEFAULT: 'var(--blue)',
					light: 'var(--blu2)',
					bg: 'var(--blbg)',
				},
				green: {
					DEFAULT: 'var(--grn)',
					bg: 'var(--gbg)',
				},
				red: {
					DEFAULT: 'var(--red)',
					bg: 'var(--rbg)',
				},
				amber: {
					DEFAULT: 'var(--amb)',
					bg: 'var(--abg)',
				},
				card: {
					DEFAULT: 'var(--card)',
					foreground: 'var(--tx)'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				primary: {
					DEFAULT: 'var(--navy)',
					foreground: '#ffffff'
				},
				secondary: {
					DEFAULT: 'var(--blue)',
					foreground: '#ffffff'
				},
				muted: {
					DEFAULT: 'var(--muted)',
					foreground: 'var(--tx2)'
				},
				accent: {
					DEFAULT: 'var(--blue)',
					foreground: '#ffffff'
				},
				destructive: {
					DEFAULT: 'var(--red)',
					foreground: '#ffffff'
				},
				border: 'var(--bdr)',
				input: 'var(--bdr)',
				ring: 'var(--blue)',
				chart: {
					'1': 'hsl(var(--chart-1))',
					'2': 'hsl(var(--chart-2))',
					'3': 'hsl(var(--chart-3))',
					'4': 'hsl(var(--chart-4))',
					'5': 'hsl(var(--chart-5))'
				}
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
