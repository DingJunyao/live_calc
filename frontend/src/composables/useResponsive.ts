// composables/useResponsive.ts
import { useDisplay } from 'vuetify'

export function useResponsive() {
  const display = useDisplay()

  return {
    display,
    isMobile: display.mobile,
    isTablet: display.sm,
    isDesktop: display.lg,
  }
}
