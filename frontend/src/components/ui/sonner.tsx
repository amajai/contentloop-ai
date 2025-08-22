import { useTheme } from "@/components/ThemeProvider"
import { Toaster as Sonner } from "sonner"

const Toaster = ({ ...props }) => {
  const { theme } = useTheme()

  return (
    <Sonner
      theme={theme === 'dark' ? 'dark' : 'light'}
      position="bottom-right"
      {...props}
    />
  )
}

export { Toaster }
