# BitHub 🎓

Welcome to the official repository for **BitHub** (available at [bithub.co.in](https://bithub.co.in)). BitHub is a student-run resource hub providing notes, previous year question papers, syllabus resources, and dashboards for Birla Institute of Technology (BIT) campuses.

---

## 📁 Repository Map

This repository is structured as a unified static site served via **GitHub Pages**. Below is an overview of the key folders and files:

```
BitHuB/
├── index.html            # Main campus selection portal (Mesra vs. Jaipur)
│
├── bit-mesra/            # BIT Mesra static site
│   ├── index.html        # Mesra homepage
│   ├── styles.css        # Stylesheet for Mesra resources
│   └── (modules/assets)  # Notes, PDFs, and curriculum resources
│
├── bit-jaipur/           # BIT Jaipur production build (DO NOT EDIT DIRECTLY)
│   ├── index.html        # Compiled dashboard entrypoint
│   ├── assets/           # Compiled and hashed JS/CSS assets
│   └── favicon.svg       # Jaipur icon assets
│
└── bit-jaipur-src/       # BIT Jaipur React + Vite source code (EDIT HERE)
    ├── src/              # React components, fonts, and assets
    ├── public/           # Static files copied to build directory
    ├── package.json      # Node scripts and dependencies
    └── vite.config.js    # Bundler and build pipeline configuration
```

---

## 🛠️ Contribution Guidelines

We welcome contributions to improve student resources for both campuses! 

- If you are contributing to the **BIT Jaipur** dashboard (React + Vite), please consult the detailed instructions in [CONTRIBUTING.md](file:///c:/Superceed_vscode/OPEN%20Source%20Contribution/BitHuB/CONTRIBUTING.md).
- **Core Contribution Rule for Jaipur:** 
  Always branch off and name your branch `bit_jaipur`. You must edit the files in `bit-jaipur-src/` and run `npm run build` so that the compiled production files in `bit-jaipur/` are updated. Commit both directories before submitting your pull request.

---

## 🚀 Technical Requirements

- **Node.js**: v16.0 or higher (recommended for compiling Jaipur assets)
- **File Encoding**: UTF-8 encoding is strictly required for all code and configuration files. Do not commit files in UTF-16LE.
- **Build Verification**: Run `npm run build` locally inside `bit-jaipur-src/` to verify compiler integrity before committing.
- **Deployment**: Any updates merged into the main/master branch are automatically deployed to [bithub.co.in](https://bithub.co.in) via GitHub Pages.

---

*Designed and Developed by Team BitHub.*
