Contributing to BitHub

Welcome to the BitHub project! This repository contains student resources for

Birla Institute of Technology campuses Mesra and Jaipur). This guide details the

contribution procedures and protocols specifically for working on the BIT Jaipur

portion of the project. Please follow these protocols to ensure a smooth, clean,

and effective collaboration.

Step-by-Step Contribution Workflow

1. Clone the Repository

Start by cloning the repository to your local system and navigating into the project

directory:git clone https://github.com/Suraj766325/BitHuB.git

cd BitHuB

2. Create the Branch

Always create a branch named bit_jaipur for your contributions related to the

Jaipur campus. Do not work directly on the master or main branch.h

git checkout -b bit_jaipur

> IMPORTANT

> To keep the commit history clean and prevent conflicts, all BIT Jaipur-related

updates must be developed on the `bit_jaipur` branch.

### 3. Local Setup & Development

The source code for the Jaipur campus is a React + Vite application located in the

`bit-jaipur-src` directory.

1.  Navigate to the source directory:

```bash

cd bit-jaipur-src

2.  Install the project dependencies:

npm install

3.  Start the local development server:

npm run dev

4.  Open the local address (typically http://localhost:3000 in your browser to

test and make edits.

4. Build the Project

After making your changes and verifying them on the development server, you

must compile the project:npm run build

This build command compiles your React source files into optimized,

production-ready static assets and places them directly into the root bit-jaipur/

directory.

Why is a Build Necessary? GitHub Pages
Hosting)

The live site bithub.co.in is hosted using GitHub Pages.

●  Static Hosting: GitHub Pages is a static file hosting service. It does not run

a Node.js server, nor does it compile React code JSX, ES6 Modules, etc.)

dynamically. It can only serve standard HTML, CSS, JavaScript, and asset

files.

●  Serving Path: The Jaipur campus website is served directly from the

bit-jaipur/ folder at the root of this repository.

●  The Compilation Step: Running npm run build inside bit-jaipur-src/

compiles the React project and outputs the files directly into bit-jaipur/.

●  Mandatory Commits: If you only modify files in the bit-jaipur-src/

directory but do not compile them, your changes will not appear on the live

site. You must run npm run build and commit the updated files in both

directories:

a.  bit-jaipur-src/ (your source code updates)

b.  bit-jaipur/ (the compiled production assets)

Protocols for Working Effectively

To maintain code quality and avoid development bottlenecks, all contributors must

adhere to these standards:

Keep Your Branch Up to Date

Before starting any new work, pull the latest changes from the upstream

repository to avoid git conflicts:# Fetch and merge updates from the main

upstream branch

git checkout master

git pull upstream master

git checkout bit_jaipur

git merge master

Never Manually Modify the Build Folder

Do not edit files inside the bit-jaipur/ directory directly. Any manual changes

in bit-jaipur/ will be permanently overwritten the next time the project is built.

Always make your modifications inside bit-jaipur-src/ and run npm run build.

Verify the Build Locally

Before staging your changes, run npm run build to ensure the compilation

completes without syntax or compiler errors. Use the local server or preview (npm

run preview) to verify the production build runs cleanly.

Write Clean Commits & PRs

1.  Stage both the source and build output:

git add bit-jaipur/ bit-jaipur-src/

2.  Commit with clear messages: Use conventional prefixes like

feat(jaipur): or fix(jaipur): to describe your changes.

git commit -m "feat(jaipur): add dynamic search filter to previous year papers"

3.  Submit a Pull Request PR Push your branch to your fork and submit a PR

from your bit_jaipur branch into the upstream master/main branch.

Thank you for contributing to BitHub! Your efforts help make campus resources

more accessible for everyone. If you run into issues, please open an issue or

reach out to the project maintainer.

Doc Prepared By : Anurag Kumar Verma

