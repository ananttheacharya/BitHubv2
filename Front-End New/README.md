# BitHub V2 — Front-End Handoff Documentation

Welcome to the new front-end folder for **BitHub V2**. This subdirectory contains a modern, production-optimized React + Vite landing page designed for elegant campus selection and a full interactive dashboard for the **Jaipur Campus**.

---

## 🚀 Features & Capabilities

1. **Aesthetic Visual System:** Warm peach/gold radial gradient background utilizing multiple vector radial gradients, CSS filters, and a subtle SVG noise grain overlay to ensure visual depth.
2. **Signature Typography:** Fully self-hosted `@font-face` integration of the premium **Advercase Bold** and **Advercase Regular** serif font families, guaranteeing robust rendering on all user devices.
3. **Campus Selection Flow:**
   - **MESRA:** Clicking *MESRA →* takes users to `../index.html` (the main, existing root BitHub platform).
   - **JAIPUR:** Clicking *JAIPUR →* renders the live, high-fidelity **Jaipur Campus Dashboard** via React state management.
4. **Jaipur Campus Dashboard:**
   - Interactive Mathematics-1 (MA24101) course dashboard.
   - Dynamic **Light / Dark Mode** theme toggle.
   - Sidebar navigation for notes (Modules 1 to 4) and syllabus access.
   - Customized **Practice Mode** generator with multiple module selection checkboxes and difficulty radio controls.
   - **Reference Books and Materials** library.
   - **Previous Year Papers** section with real-time responsive year, term, and solved/unsolved filter chips.

---

## 📁 Directory Structure

```
Front-End New/
├── dist/                  # Production-optimized compiled output
├── images/                # Campus photograph assets
│   ├── jaipur.png         # Jaipur campus photo
│   └── mesra.png          # Mesra campus photo
├── src/
│   ├── components/
│   │   ├── CampusCard.jsx # Reusable Card component
│   │   ├── Toast.jsx      # Slide-up feedback notifications
│   │   └── JaipurDashboard.jsx # Full interactive dashboard component
│   ├── fonts/             # WOFF2 Advercase font files
│   │   ├── Advercase-Bold.woff2
│   │   └── Advercase-Regular.woff2
│   ├── App.jsx            # Main app router/composer
│   ├── index.css          # Styling stylesheet & design tokens
│   └── main.jsx           # App mounting entrypoint
├── index.html             # Shell index layout (SEO optimized)
├── vite.config.js         # Build pipeline options
└── package.json           # Node dependencies
```

---

## 🛠️ Setup & Local Development

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) installed (v16.0 or higher recommended).

### 1. Install Dependencies
Navigate to the `Front-End New` directory and run:
```bash
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```
The server will start at `http://localhost:3000/` with hot-module reloading enabled.

---

## 📦 Production Deployment & Optimization

To prepare the codebase for a high-performance production deployment:

### 1. Compile the Bundle
Run the following build command:
```bash
npm run build
```

Vite will output the compiled assets inside a standalone `/dist` folder.

### 2. Optimization Details
- **Vite Config (`vite.config.js`):** Configured with `base: './'` which forces relative asset path compilation. This guarantees the bundle will run perfectly whether served from the server root, a subdirectory (e.g., `/new-frontend/`), or directly opened via file system paths.
- **Asset Inlining:** Small image icons (< 4KB) are automatically inlined directly inside CSS/JS as Base64 strings to reduce HTTP request roundtrips.
- **Cache-Busting Hashes:** Built-in hashing (e.g., `index-CKyuyCoc.css`) prevents stale caching when deploying updates.

---

## 🔌 API Integration Guidelines (For Future Backend Development)

The dashboard is structured with clean, descriptive JavaScript states to enable fast API integration when backend endpoints are ready.

Inside `src/components/JaipurDashboard.jsx`:

1. **Static Mock Variables:** Look for `const SUBJECT_DETAILS`, `const MODULES_DATA`, and `const PREVIOUS_YEAR_PAPERS`.
2. **Replacing with Live Data:**
   - Define a standard React `useEffect` inside `JaipurDashboard` to make a fetch call:
     ```javascript
     useEffect(() => {
       fetch(`/api/subjects/${SUBJECT_DETAILS.code}/papers`)
         .then(res => res.json())
         .then(data => setPapersList(data));
     }, []);
     ```
   - Bind the returned payload directly to local state variables to enable real-time updates!
