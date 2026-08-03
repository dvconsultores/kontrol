/**
 * KONTROL Design System — tokens tipados (DOC-08 §4).
 * Los valores fuente viven en theme.css; estos tokens tipados alimentan
 * componentes y utilitarios TS. Cambios requieren ADR + regresión visual.
 */

export const spacing = {
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  5: "20px",
  6: "24px",
  8: "32px",
  10: "40px",
  12: "48px",
} as const;

export const radii = {
  sm: "4px",
  md: "8px",
  lg: "12px",
} as const;

export const zIndex = {
  base: 0,
  sticky: 20,
  dropdown: 30,
  popover: 40,
  tooltip: 50,
  drawer: 60,
  dialog: 70,
  notification: 80,
} as const;

export const breakpoints = {
  mobile: 375,
  tablet: 768,
  laptop: 1024,
  desktop: 1280,
  wide: 1440,
} as const;

export const typography = {
  fontFamily: '"Ubuntu", ui-sans-serif, system-ui, sans-serif',
  scale: {
    xs: "12px",
    sm: "14px",
    base: "16px",
    lg: "18px",
    xl: "20px",
    "2xl": "24px",
    "3xl": "30px",
  },
} as const;

export const controlHeight = {
  sm: "32px",
  md: "40px",
  lg: "48px",
} as const;

export type DesignTokens = typeof spacing & {
  radii: typeof radii;
  zIndex: typeof zIndex;
  breakpoints: typeof breakpoints;
  typography: typeof typography;
  controlHeight: typeof controlHeight;
};
