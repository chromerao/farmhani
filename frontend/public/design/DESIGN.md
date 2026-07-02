---
name: Botanical Intelligence
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#404943'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#707973'
  outline-variant: '#bfc9c1'
  surface-tint: '#2c694e'
  primary: '#0f5238'
  on-primary: '#ffffff'
  primary-container: '#2d6a4f'
  on-primary-container: '#a8e7c5'
  inverse-primary: '#95d4b3'
  secondary: '#5f5f50'
  on-secondary: '#ffffff'
  secondary-container: '#e4e4cf'
  on-secondary-container: '#656555'
  tertiary: '#4a4839'
  on-tertiary: '#ffffff'
  tertiary-container: '#635f50'
  on-tertiary-container: '#dfdac6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b1f0ce'
  primary-fixed-dim: '#95d4b3'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#0e5138'
  secondary-fixed: '#e4e4cf'
  secondary-fixed-dim: '#c8c8b4'
  on-secondary-fixed: '#1b1d10'
  on-secondary-fixed-variant: '#474839'
  tertiary-fixed: '#e8e2cf'
  tertiary-fixed-dim: '#ccc6b3'
  on-tertiary-fixed: '#1e1c10'
  on-tertiary-fixed-variant: '#4a4738'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
  sage-accent: '#95D5B2'
  earth-deep: '#6B705C'
  diagnostic-red: '#E07A5F'
  growth-light: '#D8E2DC'
typography:
  display-lg:
    fontFamily: manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: manrope
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  gutter-sm: 16px
  gutter-md: 24px
  margin-sm: 20px
  margin-lg: 40px
  max-width: 1200px
---

## Brand & Style

This design system is built for a "Plant Doctor AI" service, blending the precision of medical technology with the organic tranquility of nature. The brand personality is authoritative yet nurturing—acting as a reliable expert that users can trust with their living investments.

The design style follows **Minimalism** with a heavy focus on white space and **Card-based Layouts**. It avoids clinical coldness by using organic color shifts and soft elevation, ensuring the interface feels as much like a garden as it does a diagnostic tool. The emotional response should be one of immediate relief and clarity, guiding the user through plant care with calm efficiency.

## Colors

The palette is rooted in the "Deep Forest" primary green (#2D6A4F), which represents health and professional expertise. This is balanced by "Eggshell Beige" (#F0EAD6) and "Muted Sage" (#B7B7A4) to soften the experience and provide a natural, tactile feel.

- **Primary:** Use for high-emphasis actions, active states, and brand iconography.
- **Secondary/Tertiary:** Use for decorative backgrounds, chips, and subtle differentiations between sections.
- **Neutral:** A clean, slightly warm off-white is used for the main background to reduce eye strain and provide a "paper" like quality for reading diaries and reports.
- **Named Colors:** "Diagnostic Red" is reserved for plant health alerts or critical errors, while "Sage Accent" provides a lighter alternative for progress bars and success states.

## Typography

The system utilizes a dual-font strategy. **Manrope** is used for headlines to provide a modern, refined, and geometric touch that feels technological. **Inter** is used for all body and functional text to ensure maximum legibility and a systematic, utilitarian feel necessary for data-heavy sections like cultivation diaries and diagnostic reports.

On mobile devices, display and large headlines should scale down to prevent excessive line wrapping. Maintain generous line height (1.5x for body) to ensure a relaxed reading experience suitable for educational content.

## Layout & Spacing

This design system employs a **Fixed Grid** approach for desktop and a **Fluid Grid** for mobile. The layout is centered on a 12-column system for desktop screens to house plant lists and detailed reports.

- **Desktop (1024px+):** 12 columns, 24px gutters, max-width of 1200px.
- **Tablet (768px - 1023px):** 8 columns, 20px gutters, 40px side margins.
- **Mobile (Below 768px):** 4 columns, 16px gutters, 20px side margins.

Vertical rhythm follows an 8px base unit. Spacing between cards should generally be 24px to allow the soft shadows to breathe.

## Elevation & Depth

Visual hierarchy is established using **Tonal Layers** combined with **Ambient Shadows**. Surfaces are tiered to represent the depth of information:

1.  **Background:** The lowest layer, using the neutral light-gray or light-beige.
2.  **Cards:** Raised surfaces with a 16px blur radius and 5% opacity black shadow, tinted slightly with the primary green hue to maintain color harmony.
3.  **Active/Hover States:** Cards slightly increase in shadow depth and lift (2px) to provide tactile feedback.

Glassmorphism is used sparingly for navigation overlays and photo upload modals to maintain context of the background plant imagery.

## Shapes

The shape language is consistently "Rounded" to echo the soft curves of leaves and petals.

- **Containers & Cards:** Use `rounded-lg` (16px) for the main card structures as requested.
- **Buttons & Inputs:** Use `rounded` (8px) for a slightly tighter, more functional appearance.
- **Chips & Tags:** Use pill-shaped (100px) rounding for status indicators (e.g., "Healthy", "Needs Water").
- **Image Containers:** Should always match the corner radius of their parent card.

## Components

### Buttons
- **Primary:** Solid #2D6A4F background with white text. High contrast, 8px corner radius.
- **Secondary:** Outlined with a 1px border of #2D6A4F and a subtle light-sage background on hover.
- **Ghost:** No background or border, used for secondary actions like "Cancel" or "Skip."

### Cards
Cards are the primary container for plant profiles and AI results. They feature a 16px corner radius, a subtle 1px border (#B7B7A4 at 20% opacity), and the standard ambient shadow.

### Input Fields
Inputs should be clean with a light beige (#F0EAD6) background and an 8px corner radius. On focus, the border should transition to the primary green with a soft outer glow.

### Chips
Used for plant categories or health status. "Healthy" chips use a soft green background; "Warning" chips use a soft diagnostic-red. All chips are pill-shaped.

### Plant Health Gauge
A unique component for this system—a circular or semi-circular progress bar using the "Sage Accent" to show the health score or moisture levels.

### Photo Upload Area
A large, dashed-border drop zone with `rounded-xl` corners, using a light green tint to invite user interaction for AI analysis.
