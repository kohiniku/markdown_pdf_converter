## Design Spec
### Tone & Brand
- Minimal / Professional / Calm
### Layout
- Header / Sidebar / Main の3領域。Mainは上から Cards → Filters → Table。
### Tokens
- Font: Inter, Noto Sans JP; base 14px
- Colors: 
  - bg: #0B1020
  - surface: #11162A
  - text: #E6E8EF
  - primary: #4F8DF7
  - border: #1E2743
  - muted: #A0A7C1
- Radius: 14px / Shadow: soft
- Spacing scale: 4, 8, 12, 16, 24, 32, 48
### Components
- Button(Primary/Outline/Text): hover=明度+8%, focus:ring, disabled=0.6 opacity
- Card: section化（header/body/footer）, padding 16
- Input: focus-visible outline 2px primary, error styles
- Table: roomy rows, sticky header, empty/loading/error states
### Responsiveness
- sm(<768px): sidebar collapsible, 1-col cards, table scroll-x
### Accessibility
- Contrast ≥ 4.5:1, keyboard-friendly, aria-label
### Don’ts
- 多色/過剰な境界/密集
# Design Foundation

This project uses Tailwind CSS with CSS variable–driven theming (light/dark) and a small set of reusable UI components.

## Theme Tokens (CSS Variables)

Declared in `frontend/assets/css/theme.css` and mapped in `tailwind.config.ts`.

- Roles: `--background`, `--foreground`, `--card`, `--card-foreground`, `--muted`, `--muted-foreground`, `--border`, `--input`, `--primary`, `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--accent`, `--accent-foreground`, `--ring`.
- Light and dark values are defined on `:root` and `.dark`.
- Tailwind aliases: `bg-background`, `text-foreground`, `bg-card`, `text-muted-foreground`, `border-border`, `bg-primary`, etc.

## Dark Mode

- Strategy: `darkMode: 'class'` (Tailwind)
- Class applied to `<html>` by `frontend/plugins/theme.client.ts`
- User preference is stored in `localStorage('theme')` via `useTheme()` composable.

## Components

Location: `frontend/components/ui`

- `UiButton`: variants `primary|secondary|ghost`, sizes `sm|md|lg`
- `UiSelect`: styled `<select>` with `v-model`
- `UiCard`: card container with optional `#header` slot
- `UiSkeleton`: loading placeholder (`w`, `h` props)
- `UiSwitch`: boolean switch for dark mode

## Layout

- `layouts/default.vue` provides sticky header and a centered container (`max-w-6xl`).
- `components/AppHeader.vue` includes brand, Home action, and dark-mode toggle.
- `pages/index.vue` uses a responsive grid: chart + reasoning (2 cols) and news panel (1 col).

## Usage Guidelines

- Spacing: prefer Tailwind scale (`gap-3`, `p-4`) and keep vertical rhythm consistent.
- Cards: use `UiCard` for panels. Place section titles in the `#header` slot.
- Forms: use `UiSelect` and `@tailwindcss/forms` for consistent inputs.
- Typography: leverage `text-muted-foreground` for secondary text.
- Borders: use `border-border` and `shadow-card` for elevation level 1.

## Future Extensions

- Add `UiTabs`, `UiBadge`, and `UiAlert` as needed.
- Chart theme: align ApexCharts palette with `--primary`/`--muted` colors.
- Motion: introduce subtle transitions for page changes.
