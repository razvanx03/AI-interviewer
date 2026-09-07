# Login Page (`app/src/pages/LoginPage.tsx`)

## 1. Overview
The `LoginPage` component provides an authentication portal for recruiters and administrators before accessing restricted dashboard features (candidate screening, interview creation, and evaluation report reviews).

## 2. Features
- **Clean Authentication Form**: Email/username and password input fields with form validation.
- **Theme & Language Switchers**: Integrated header bar allowing live toggle between Light/Dark themes and Romanian/English translations.
- **Generic Error Handling**: Clean error reporting without leaking internal default credentials.
- **Auto Redirect**: Redirects authenticated users directly to their requested destination route via React Router's `location.state.from`.
