# Frontend Reorganization Plan

## Current Structure Issues
1. **Ingredients.jsx** is a page but located in `components/`
2. **Auth components** (Login, Signup) mixed with other components
3. **Naming inconsistency**: `addCocktailForm.jsx` should be PascalCase
4. **CSS files** scattered (Auth.css in components, App.css in root)
5. **No separation** for hooks, utils, or layout components

## Recommended Structure

```
src/
├── api/
│   └── index.js                    # API client (renamed from api.js)
│
├── assets/
│   └── react.svg
│
├── components/
│   ├── cocktail/
│   │   └── AddCocktailForm.jsx     # Renamed from addCocktailForm.jsx
│   ├── ingredient/
│   │   └── IngredientForm.jsx      # Extract form logic from Ingredients page
│   ├── layout/
│   │   ├── Navbar.jsx              # Extract navbar from App.jsx
│   │   └── ProtectedRoute.jsx       # Move here
│   └── common/                      # Shared/reusable components
│       └── LoadingSpinner.jsx      # Extract loading logic
│
├── contexts/
│   ├── AuthContext.jsx             # ✅ Already good
│   └── AuthProvider.jsx             # ✅ Already good
│
├── hooks/
│   ├── useCocktails.js              # Custom hook for cocktails logic
│   ├── useIngredients.js            # Custom hook for ingredients logic
│   └── useApi.js                    # Custom hook for API calls
│
├── pages/
│   ├── CocktailsPage.jsx            # ✅ Already good
│   ├── IngredientsPage.jsx         # Move from components/Ingredients.jsx
│   ├── auth/
│   │   ├── LoginPage.jsx           # Move from components/Login.jsx
│   │   └── SignupPage.jsx          # Move from components/Signup.jsx
│   └── NotFoundPage.jsx            # Add 404 page
│
├── styles/
│   ├── index.css                   # Global styles (move from root)
│   ├── App.css                     # App-specific styles
│   ├── auth.css                    # Auth styles (move from components/Auth.css)
│   └── variables.css               # CSS variables/theme
│
├── utils/
│   ├── constants.js                 # App constants
│   └── helpers.js                   # Utility functions
│
├── App.jsx                          # Main app component
├── main.jsx                         # Entry point
└── routes.jsx                       # Route configuration (optional)

```

## Benefits of This Structure

1. **Clear separation**: Pages vs components vs utilities
2. **Better organization**: Related files grouped together
3. **Scalability**: Easy to add new features
4. **Maintainability**: Easier to find and update code
5. **Consistency**: PascalCase for components, clear naming

## Migration Steps

1. Create new folder structure
2. Move files to appropriate locations
3. Update all import paths
4. Rename files to follow conventions
5. Extract reusable logic into hooks
6. Organize CSS files

## Priority Changes (Quick Wins)

1. **High Priority:**
   - Move `Ingredients.jsx` → `pages/IngredientsPage.jsx`
   - Move `Login.jsx` → `pages/auth/LoginPage.jsx`
   - Move `Signup.jsx` → `pages/auth/SignupPage.jsx`
   - Rename `addCocktailForm.jsx` → `AddCocktailForm.jsx`

2. **Medium Priority:**
   - Extract navbar from `App.jsx` → `components/layout/Navbar.jsx`
   - Move `ProtectedRoute.jsx` → `components/layout/ProtectedRoute.jsx`
   - Organize CSS files into `styles/` folder

3. **Low Priority (Future):**
   - Create custom hooks for data fetching
   - Extract form components
   - Add utility functions

