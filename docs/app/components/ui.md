# UI Component Primitives (`app/src/components/ui/`)

All primitives are based on accessible **Radix UI** components and styled with Tailwind design tokens (Zinc/Neutral base):

| Component | File | Base Primitive | Description |
|---|---|---|---|
| `Button` | `button.tsx` | `@radix-ui/react-slot` | Supports variants: default, secondary, outline, destructive, ghost, link |
| `Card` | `card.tsx` | `div` | Header, Title, Description, Content, Footer |
| `Input` | `input.tsx` | `input` | Accessible styled input |
| `Textarea` | `textarea.tsx` | `textarea` | Auto-styled multiline input |
| `Select` | `select.tsx` | `@radix-ui/react-select` | Accessible styled dropdown with animations and checkmarks |
| `Badge` | `badge.tsx` | `div` | Variants: default, secondary, outline, success, destructive |
| `Label` | `label.tsx` | `@radix-ui/react-label` | Accessible form labels |
| `Separator`| `separator.tsx`| `@radix-ui/react-separator` | Horizontal / vertical divider |
| `Dialog` | `dialog.tsx` | `@radix-ui/react-dialog` | Accessible modal dialog with backdrop |
| `DropdownMenu` | `dropdown-menu.tsx` | `@radix-ui/react-dropdown-menu` | Accessible dropdown menu for actions & theme switcher |
