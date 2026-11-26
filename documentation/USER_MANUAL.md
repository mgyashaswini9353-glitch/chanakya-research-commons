# Chanakya Research Commons — Complete User Manual & Technology Guide

**Chanakya University · Campus Research & Collaboration Platform**  
*All-in-One Complete Guide: Every Page, Feature, Step-by-Step Workflow, and Underlying Technology*

---

## Table of Contents

1. [Platform Overview & User Roles](#1-platform-overview--user-roles)
2. [Getting Started & Demo Credentials](#2-getting-started--demo-credentials)
3. [Header, Navigation & Global Controls](#3-header-navigation--global-controls)
4. [Complete Page-by-Page Guide (All 19 Pages)](#4-complete-page-by-page-guide-all-19-pages)
   - [4.1 Landing Page (`/`)](#41-landing-page-)
   - [4.2 Sign In (`/login`)](#42-sign-in-login)
   - [4.3 Create Account / Registration (`/register`)](#43-create-account--registration-register)
   - [4.4 Home Dashboard (`/dashboard`)](#44-home-dashboard-dashboard)
   - [4.5 Community Discussions (`/discussions`)](#45-community-discussions-discussions)
   - [4.6 Start a Discussion / Full Post Editor (`/discussions/new`)](#46-start-a-discussion--full-post-editor-discussionsnew)
   - [4.7 Explore Research (`/discover`)](#47-explore-research-discover)
   - [4.8 Research Search — Unified 4-Category Search (`/search`)](#48-research-search--unified-4-category-search-search)
   - [4.9 Publication Details (`/papers/:id`)](#49-publication-details-papersid)
   - [4.10 My Library & Shared University Library (`/library`)](#410-my-library--shared-university-library-library)
   - [4.11 Personal Collections (`/collections`)](#411-personal-collections-collections)
   - [4.12 People / Researchers Directory (`/researchers`)](#412-people--researchers-directory-researchers)
   - [4.13 Academic Member Profile (`/researchers/:id`)](#413-academic-member-profile-researchersid)
   - [4.14 Recommended for You (`/recommendations`)](#414-recommended-for-you-recommendations)
   - [4.15 Research Trends (`/trends`)](#415-research-trends-trends)
   - [4.16 Research Assistant (`/assistant`)](#416-research-assistant-assistant)
   - [4.17 Account & Profile Settings (`/settings`)](#417-account--profile-settings-settings)
   - [4.18 Institutional Insights — Admin Only (`/analytics`)](#418-institutional-insights--admin-only-analytics)
   - [4.19 Administration & Moderation — Admin Only (`/admin`)](#419-administration--moderation--admin-only-admin)
5. [Complete Technology Stack & Architecture Reference](#5-complete-technology-stack--architecture-reference)
6. [Data Engineering, Data Warehouse & Star Schema Guide](#6-data-engineering-data-warehouse--star-schema-guide)
7. [Data Mining, Machine Learning & RAG Algorithms Explained](#7-data-mining-machine-learning--rag-algorithms-explained)
8. [Verified Dataset Counts & Executed Evaluation Benchmarks](#8-verified-dataset-counts--executed-evaluation-benchmarks)
9. [Running Locally, Docker Compose & Troubleshooting](#9-running-locally-docker-compose--troubleshooting)

---

## 1. Platform Overview & User Roles

**Chanakya Research Commons** is Chanakya University's unified digital research community where students, faculty members, researchers, and administrators discover scholarly papers, organize shared and personal libraries, exchange ideas through discussions, track emerging campus research trends, ask evidence-grounded questions, and analyze institutional research activity.

### User Roles & Access Permissions (RBAC)

| Role | Who It Is For | Access Scope |
|---|---|---|
| **Student** | Undergraduate & postgraduate students | Full community access: Home feed, Discussions (create/edit/delete own posts, like, comment, reply, save posts), Explore, Research Search, My Library & Collections, Researchers Directory, Recommended for You, Research Trends, Research Assistant, Settings. |
| **Faculty** | Professors & department mentors | Same full community & research access as Students, displayed with Faculty academic affiliation across profiles, discussions, and researcher discovery. |
| **Researcher** | Postdoctoral fellows & research scholars | Same full community & research access as Students/Faculty, highlighted under Researcher filters. |
| **Administrator** | Deans, research coordinators & platform admins | Everything above **plus** two restricted sections protected by role-based access control: **Institutional Insights (`/analytics`)** and **Administration & Moderation (`/admin`)**, plus ability to moderate any post or flagged account. |

---

## 2. Getting Started & Demo Credentials

### Access URLs
- **Local Development**: Frontend at `http://localhost:5173/` · Backend Swagger API Docs at `http://localhost:8000/docs`
- **Docker Compose**: Frontend at `http://localhost:3000/` · Backend API at `http://localhost:8000/docs` · MinIO Object Storage Console at `http://localhost:9001`

### Sample Member Accounts (All 4 Roles)
All demo accounts use the password **`Chanakya@2026`** (and are also available inside the collapsible *"Quick sign-in with sample member accounts"* drawer on `/login`):

| Role | Name | Email | Department |
|---|---|---|---|
| **Student** | Aarav Nair | `student@chanakya.edu.in` | Data Science & Engineering (`DSE`) |
| **Faculty** | Dr. Ananya Deshpande | `faculty@chanakya.edu.in` | Computer Science & AI (`CSAI`) |
| **Researcher** | Dr. Rohan Kulkarni | `researcher@chanakya.edu.in` | Biotechnology & Bioinformatics (`BIO`) |
| **Administrator** | Dr. Vikramaditya Rao | `admin@chanakya.edu.in` | Data Science & Engineering (`DSE`) |

---

## 3. Header, Navigation & Global Controls

The sticky header (`frontend/src/layouts/AppLayout.tsx`) appears across all internal pages with a subtle Chanakya Gold `#D6AA35` top bar:

1. **Official Chanakya University Logo** (left) — Undistorted transparent official university crest + `"Research Commons"` subtitle. Clicking navigates to `/dashboard` (when signed in) or `/` (when logged out).
2. **Primary Navigation Links** (center):
   - **Home** (`/dashboard`) — Personalized community homepage & campus feed
   - **Community** (`/discussions`) — Full discussions, threads & saved posts
   - **Explore** (`/discover`) — Image-led research discovery & filterable publication catalog
   - **Research** (`/search`) — Unified 4-category search across Papers, Library, People & Discussions
   - **My Library** (`/library`) — Saved papers, saved posts, shared university library & reading history
3. **Compact Search Field** — Enter any keyword and press Enter from any page to jump straight to `/search?q=...`.
4. **Notifications Bell** — Opens a live dropdown showing recent followers, replies on your posts, and emerging campus topics (`GET /api/notifications`).
5. **User Profile Dropdown** — Quick access to:
   - My Profile (`/researchers/:id`)
   - People Directory (`/researchers`)
   - Recommended for You (`/recommendations`)
   - Research Assistant (`/assistant`)
   - Research Trends (`/trends`)
   - My Collections (`/collections`)
   - Account Settings (`/settings`)
   - *(Admin only)* **Institutional Insights** (`/analytics`) & **Administration** (`/admin`)
   - Sign Out
6. **Responsive Mobile Drawer** — On phones and tablets (`< 1024px`), collapses neatly into a slide-down menu button with search and all navigation links.

**Technology Behind the Shell**: React 18, React Router v6 (`<Outlet />`, `<NavLink>`), Tailwind CSS custom Chanakya tokens (`#142B4A`, `#D6AA35`, `#FAF8F2`, `#E9EFE8`), Lucide React icons, JWT `AuthContext`, and global `ToastContext` notifications.

---

## 4. Complete Page-by-Page Guide (All 19 Pages)

---

### 4.1 Landing Page (`/`)
- **Access**: Public (guests & signed-in members)
- **File**: `frontend/src/pages/LandingPage.tsx`
- **What Is on This Page**:
  1. **Clean Navigation Bar**: Official Chanakya University logo, quick links (`Community`, `Explore`, `Research`, `People`), and `Sign in` / `Join Community` buttons.
  2. **Campus Welcome Hero**: Features the headline *"Ideas grow when we share them."*, two action buttons (`Explore Community`, `Discover Research`), an instant research search bar with clickable topic chips, and the sunlit Chanakya University Global Campus photograph (`campus.jpg`).
  3. **Campus Life & Learning Cards**: Three real campus photography cards (`Workshop5.jpg`, `classroom.jpg`, `Sports.jpg`) highlighting seminars, the shared library, and cross-departmental connections.
  4. **Explore Research Across Departments**: Live cards for all 6 Chanakya University departments (`CSAI`, `DSE`, `ECE`, `BIO`, `MGT`, `REM`) showing active member counts and linking directly into department-filtered discovery.
  5. **Papers Students & Faculty Are Reading**: Top 4 most-saved publications from the shared Chanakya University library.
  6. **Connect with Fellow Researchers**: Live directory preview of active campus members.
  7. **Closing Invitation Banner** (with `CU-logo.jpg` Administration Block photo) and clean institutional footer.
- **Behind-the-Scenes Technology**: Fetches live data in parallel from `GET /api/departments`, `GET /api/papers?only_library=true&sort=saves&limit=4`, and `GET /api/users?limit=4` via FastAPI + SQLAlchemy; serves locally bundled official campus photography from `frontend/public/images/chanakya/`.

---

### 4.2 Sign In (`/login`)
- **Access**: Public
- **File**: `frontend/src/pages/LoginPage.tsx`
- **What Is on This Page**:
  - **Left Panel (Desktop)**: Full-bleed Chanakya University campus photograph (`campus.jpg`) with warm deep-navy veil and the official Chanakya logo in a crisp white badge.
  - **Right Panel**: University email/username input, password input with show/hide visibility toggle (`Eye`/`EyeOff`), inline error messages, loading spinner, and a discreet collapsible *"Quick sign-in with sample member accounts"* drawer for one-click login as Student, Faculty, Researcher, or Administrator.
- **Behind-the-Scenes Technology**: Calls `POST /api/auth/login`. Backend (`backend/app/core/security.py`) verifies credentials using **`bcrypt`** password hashing and issues an HS256 **JWT Bearer Token** (`PyJWT`, 24-hour expiry) stored in `localStorage` via `AuthContext`.

---

### 4.3 Create Account / Registration (`/register`)
- **Access**: Public
- **File**: `frontend/src/pages/RegisterPage.tsx`
- **What Is on This Page**:
  - **Left Panel**: Chanakya University campus learning infrastructure photo (`CU-New-Campus-Infra_246.jpg`) with official logo.
  - **Right Panel**: Full Name, University Email, optional Username (auto-derived if left blank), Password with live visibility toggle and real-time password strength checklist (`6+ characters`, `Letters`, `Number`), Academic Role selector (`Student`, `Faculty`, `Researcher`), Department dropdown (populated live from `/api/departments`), free-text Research Interests, and comma-separated Areas of Interest tags.
- **How It Works**: Upon submitting, the backend creates the user, hashes the password with `bcrypt`, automatically subscribes the member to their listed research topics in `topic_follows`, logs them in immediately, and redirects to `/dashboard` (where Cold-Start recommendations immediately activate!).
- **Behind-the-Scenes Technology**: `POST /api/auth/register` with **Pydantic v2** email & schema validation (`email-validator`), SQLAlchemy unique email/username enforcement, and automatic JWT issuance.

---

### 4.4 Home Dashboard (`/dashboard`)
- **Access**: Public preview; full personalized workspace when signed in
- **File**: `frontend/src/pages/DashboardPage.tsx`
- **What Is on This Page**:
  1. **Compact Campus Welcome Banner**: Features `CU-logo.jpg`, *"Ideas grow when we share them."*, and quick `Explore Community` / `Discover Research` buttons.
  2. **Left Sidebar**:
     - **Member Profile Card**: Navy header with gold accent line, initials avatar, role & department, live counters for `Saved papers`, `Collections`, and `Following`.
     - **Areas of Interest**: Clickable research topic pills + `Edit` link to Settings.
     - **Recently Viewed**: Your most recently opened papers (`GET /api/library/recently-viewed`).
  3. **Center Column (Main Community Focus)**:
     - **Inviting Post Composer**: Placeholder *"What's something interesting you're working on?"* — expands inline to enter headline, body, and topics, or jump to the Full Editor to attach a library paper.
     - **Feed Filter Tabs**: `For You` (personalized), `Following` (people you follow), `Recent` (all campus posts), and `Saved Posts` (your bookmarked discussions).
     - **Community Post Cards**: Author avatar, name, role, department, relative timestamp, subtle `Sample` tag on synthetic demo posts to distinguish them from real member posts, attached paper card (if present), clickable topic pills, **Like** (`Heart`), **Comment count**, **Save Post** (`Bookmark`), plus **Edit modal** & **Delete confirmation** for your own posts (or Admin).
     - **Interleaved Suggested Reading**: A personalized `PaperCard` seamlessly woven into the feed.
  4. **Right Sidebar**:
     - **Campus Research Spotlight** card (`Workshop5.jpg`).
     - **People to Connect With** (1-click Follow).
     - **Topics on Campus** (highlighting rising topics with a warm gold `Rising` badge).
     - **Recommended Reading** list.
- **Behind-the-Scenes Technology**: Integrates `GET /api/posts?feed=personalized|following|all|saved`, `POST /api/posts`, `PATCH /api/posts/{id}`, `DELETE /api/posts/{id}`, `POST /api/posts/{id}/upvote`, `POST /api/posts/{id}/save`, `GET /api/recommendations/papers`, `GET /api/recommendations/researchers`, `GET /api/trends`, and `GET /api/library/recently-viewed`. Personalized ranking weights followed authors, followed topics, upvotes, replies, and recency.

---

### 4.5 Community Discussions (`/discussions`)
- **Access**: Public read; signed-in members can post, like, comment, reply, save, edit/delete own posts
- **File**: `frontend/src/pages/DiscussionsPage.tsx`
- **What Is on This Page**:
  - **5 Feed Tabs**: `For You`, `Following`, `My Topics`, `Saved Posts`, and `All Community`.
  - **Left Column (7/12)**: Scrollable list of discussion cards with Like, Reply count, Save Post bookmark, Edit modal, and Delete confirmation dialog.
  - **Right Sticky Thread Viewer (5/12)**: Click any post to open its complete text, all top-level comments, indented **nested replies**, inline `"Reply"` button on any comment, and live comment composer at the bottom.
- **Behind-the-Scenes Technology**: Backed by `posts`, `comments` (self-referencing `parent_comment_id`), `post_upvotes`, and `saved_posts` tables in SQLAlchemy/PostgreSQL. Every post, comment, and upvote also records a telemetry row in `activity_events` to power Trends and Institutional Insights.

---

### 4.6 Start a Discussion / Full Post Editor (`/discussions/new`)
- **Access**: Signed-in Members
- **File**: `frontend/src/pages/CreatePostPage.tsx`
- **What Is on This Page**:
  - Full-width post composer for longer research updates: Discussion Headline, Discussion Body, comma-separated Topics, searchable dropdown to **Attach a Paper from the Chanakya University Library** (pre-filled automatically if opened via *"Discuss with Community"* from a Paper Detail page), and an optional External Link field.
- **Behind-the-Scenes Technology**: `POST /api/posts` validates inputs with Pydantic `PostCreateRequest`, links `attached_paper_id` via foreign key, and logs a `post` event in `activity_events`.

---

### 4.7 Explore Research (`/discover`)
- **Access**: Public (Save button active when signed in)
- **File**: `frontend/src/pages/DiscoveryPage.tsx`
- **What Is on This Page**:
  1. **3 Image-Led Campus Explore Cards**: Clickable cards featuring real campus photos (`Workshop5.jpg` → Seminars & AI, `Sustainability-Web-Banner.jpg` → Clean Energy & Materials, `CU-New-Campus-Infra_241.jpg` → Meet Mentors & Peers).
  2. **Approachable Discovery Search Bar**: Live text filter + popular topic suggestion chips + *"Full Campus Search"* button.
  3. **Left Filter Sidebar**: Department selector, Author name filter, Published Since year dropdown, Sort Order (`Most Saved on Campus`, `Most Cited`, `Most Influential`, `Newest First`), secondary Archive Source filter (`OpenAlex`, `arXiv`, `Research Feeds`), and `Topics People Explore` cloud.
  4. **Paginated Publication Feed**: Clean `PaperCard` results (10 per page with `Previous` / `Next` controls) showing title, authors, year, venue, abstract snippet, topics, citation count, campus save count, source names, `Save` button, and `Open` link.
- **Behind-the-Scenes Technology**: Queries `GET /api/papers` with server-side SQL filtering & pagination (`department`, `author`, `year_from`, `source`, `q`, `sort=saves|citations|pagerank|recent`), where `"Most Influential"` ranks papers by their precomputed **NetworkX Citation Graph PageRank** score.

---

### 4.8 Research Search — Unified 4-Category Search (`/search`)
- **Access**: Public (Save button active when signed in)
- **File**: `frontend/src/pages/UnifiedSearchPage.tsx`
- **What Is on This Page**:
  1. **Unified Search Bar**: One query searches all four university data categories simultaneously, with clickable example queries and a direct link to the Research Assistant.
  2. **Expandable `"More search options"` Drawer**: Keeps advanced options cleanly tucked away for everyday students while giving full control over:
     - **Search Mode**: `Smart Search` (Hybrid), `Concept Match` (Semantic), or `Exact Terms` (Keyword)
     - **Filters**: Department, Source, Publication Year
  3. **5-Tab Result Bar with Live Counts**:
     - `All Results` (2×2 unified view showing all 4 categories side-by-side!)
     - `Papers` (External open scholarly papers, deduplicated across sources)
     - `Library` (Papers saved in the shared Chanakya University Library)
     - `People` (Matching students, faculty & researchers)
     - `Discussions` (Matching campus posts & threads)
- **Behind-the-Scenes Technology (Subsystem F5)**:
  - Calls `GET /api/search/unified` (`ml/search/search_engine.py`).
  - **Keyword Scoring**: Multi-field weighted BM25/TF-IDF over title (`2.6×`), topics (`2.2×`), authors (`1.6×`), venue (`0.9×`), and log-TF abstract.
  - **Semantic Scoring**: Cosine similarity over **384-dimensional dense vectors** (`sentence-transformers/all-MiniLM-L6-v2` in Docker / persisted 384-d TF-IDF+TruncatedSVD LSA fallback on Python 3.14; `pgvector` HNSW index in PostgreSQL).
  - **Hybrid Mode**: **Reciprocal Rank Fusion (RRF)** combining Keyword + Semantic ranks + **NetworkX Citation PageRank** boost.
  - **Duplicate Prevention**: Papers ingested from multiple sources (e.g., OpenAlex + arXiv) are merged via **MinHash + LSH (`datasketch`) + Author Entity Resolution** so each paper appears once with all contributing sources listed. Every search logs a `search` telemetry event into `activity_events`.

---

### 4.9 Publication Details (`/papers/:id`)
- **Access**: Public read; signed-in members can save, assign collection, and write private notes
- **File**: `frontend/src/pages/PaperDetailPage.tsx`
- **What Is on This Page**:
  - **Main Column**: Publication year, venue, campus save badge, full title, complete author list, citation count, DOI, arXiv ID, indexed source names, complete readable abstract, clickable topic pills, and action buttons (`Read Publication`, `Open PDF`, `Discuss with Community`).
  - **"People who saved this paper also explored"**: Curated grid of related publications frequently saved together by campus members.
  - **Right Sidebar**:
    - **My Library & Private Notes**: Assign the paper to a Personal Collection, write/edit private reading notes (visible only to you), and Save or Remove.
    - **Saved on Campus**: List of Chanakya members who saved this paper (clickable to their profiles).
    - **Related Discussions**: Community threads referencing this paper.
- **Behind-the-Scenes Technology**:
  - `GET /api/papers/{id}` automatically logs a `view` event (feeding `Recently Viewed`, `Research Trends`, and `Institutional Insights`).
  - *"People who saved this paper also explored"* is powered by **FP-Growth Association Rule Mining (`mlxtend.frequent_patterns.fpgrowth` + `association_rules`)** over member paper-save baskets (`ml/recommendations/recommender.py`), with co-save lift and semantic similarity fallbacks for rare papers.

---

### 4.10 My Library & Shared University Library (`/library`)
- **Access**: University Library is public; personal tabs require sign-in
- **File**: `frontend/src/pages/UniversityLibraryPage.tsx`
- **What Is on This Page**:
  - **4 Clean Tabs**:
    1. `Saved Papers` — Every paper you have saved (`GET /api/library/my`)
    2. `Saved Posts` — Every community post you have bookmarked (`GET /api/posts?feed=saved`)
    3. `University Library` — Shared campus-wide catalog of all papers saved by any Chanakya member, sortable by `Most Saved on Campus`, `Most Cited`, or `Newest First`
    4. `Recently Viewed` — Your last 20 viewed publications (`GET /api/library/recently-viewed`)
  - **`Collections` Button**: Opens `/collections`.
  - **`Add Publication` Modal**: Paste a **DOI**, **arXiv ID**, or **URL** (plus optional title, topics, and private notes). Automatically fetches live metadata from OpenAlex or arXiv, prevents duplicates, computes its 384-d vector embedding, adds it to your library, and updates the shared university library!
- **Behind-the-Scenes Technology**: Backed by `saved_papers`, `saved_posts`, `collections`, and `papers` tables; live identifier lookup (`POST /api/papers/add-by-identifier`) calls the OpenAlex & arXiv APIs via `httpx` + XML ElementTree (`ingestion/pipeline.py`) and deduplicates via `PaperDeduplicator`.

---

### 4.11 Personal Collections (`/collections`)
- **Access**: Signed-in Members
- **File**: `frontend/src/pages/CollectionsPage.tsx`
- **What Is on This Page**:
  - **Left Sidebar**: List of all personal reading folders with item counts, inline **Rename** button, **Delete** button (with safe `ConfirmDialog`), and a **New Collection** creator form.
  - **Main Area**: Papers inside the selected collection, per-paper collection dropdown to move items between folders, and inline **Private Notes** viewer/editor.
- **Behind-the-Scenes Technology**: Full CRUD REST API (`GET/POST /api/collections`, `PATCH/DELETE /api/collections/{id}`, `PATCH /api/library/save/{paper_id}`) backed by SQLAlchemy foreign keys with `ON DELETE SET NULL` so deleting a folder never deletes your saved papers.

---

### 4.12 People / Researchers Directory (`/researchers`)
- **Access**: Public read; Follow buttons active when signed in
- **File**: `frontend/src/pages/ResearchersPage.tsx`
- **What Is on This Page**:
  - Search bar (name, research area, or topic), Department filter dropdown, Role filter (`Faculty`, `Researcher`, `Student`), and a responsive 3-column grid of academic member cards showing initials avatar, full name, role, department, research bio, interest pills, follower & saved-paper counts, and instant **Follow / Following** toggle button.
- **Behind-the-Scenes Technology**: `GET /api/users` excludes spam-flagged accounts automatically; `POST`/`DELETE /api/users/{id}/follow` manages `user_follows` and logs follow activity events.

---

### 4.13 Academic Member Profile (`/researchers/:id`)
- **Access**: Public read; Follow / Edit Profile active when signed in
- **File**: `frontend/src/pages/ResearcherProfilePage.tsx`
- **What Is on This Page**:
  - Framed with the Chanakya University `CampusArch.jpg` architectural banner + gold accent bar, circular initials avatar, name, role, department, biography, follower/following/saved/discussion counters, personal website link, and `Connect & Follow` (or `Edit Profile`) button.
  - **3 Profile Tabs**:
    1. `About & Interests` — Research statement, clickable topic pills, and external Publication/ORCID/Scholar links.
    2. `Reading & Publications` — Papers recently saved by this member.
    3. `Contributions` — Community discussions authored by this member.
- **Behind-the-Scenes Technology**: `GET /api/users/{id}` aggregates relational data across `users`, `departments`, `user_follows`, `saved_papers`, and `posts`.

---

### 4.14 Recommended for You (`/recommendations`)
- **Access**: Signed-in Members
- **File**: `frontend/src/pages/RecommendationsPage.tsx`
- **What Is on This Page**:
  1. **Publications You May Want to Read**: Personalized papers with natural-language explanations (e.g., *"Members with similar research interests saved this"*, *"Because you follow Federated Learning"*, *"Related to your research interests"*).
  2. **Researchers with Shared Interests**: Colleagues to connect with + shared-interest explanations + 1-click Follow buttons.
  3. **Discussions in Your Areas**: Community threads matching your followed topics and network.
- **Behind-the-Scenes Technology (Subsystem F6)**:
  - **Papers** (`GET /api/recommendations/papers`): Hybrid **Content-Based Filtering** (cosine similarity between user profile + saved-paper centroid and candidate paper embeddings) + **User-Item Collaborative Filtering** (cosine similarity over member-paper save matrix) + automatic **Cold-Start** blending (profile similarity + tag Jaccard + department affinity + citation popularity) for brand-new users with zero history.
  - **Researchers** (`GET /api/recommendations/researchers`): Combines interest-profile embeddings, tag Jaccard, shared saved papers, 2-hop social graph proximity, and **NetworkX Greedy Modularity Community Detection**.

---

### 4.15 Research Trends (`/trends`)
- **Access**: Public (Topic Follow buttons active when signed in)
- **File**: `frontend/src/pages/TrendsPage.tsx`
- **What Is on This Page**:
  - **Time Window Selector**: `Past 2 Weeks`, `Past Month`, `Past 2 Months`.
  - **Emerging Research Areas**: Highlight cards phrased naturally (e.g., *"Growing interest in Solid State Batteries"*) showing peak-week activity vs typical baseline volume.
  - **Research Activity Over Time Chart**: Clean multi-line interactive chart (Recharts) showing weekly activity across leading campus topics.
  - **Popular Research Topics Table**: Activity counts, period-over-period growth %, `Rising` badge, and 1-click `Follow / Following` buttons.
  - **Popular Discussions**: Sidebar of active campus threads.
- **Behind-the-Scenes Technology (Subsystem F7)**: `GET /api/trends` (`ml/trend_detection/trends.py`) executes **sliding-window stream statistics** over `activity_events` (excluding spam-flagged accounts), computing leave-one-out historical mean/std and **Z-score spike detection** (`Z >= 3.0`) to identify genuine sudden topic surges.

---

### 4.16 Research Assistant (`/assistant`)
- **Access**: Public & Signed-in Members
- **File**: `frontend/src/pages/AssistantPage.tsx`
- **What Is on This Page**:
  - **Two-Pane Scholarly Q&A Workspace**:
    - **Left Pane**: Natural-language question box, optional *"Limit sources to publications saved in the university library"* checkbox, 5 suggested research questions, and conversation history of answers with real bold formatting and **clickable `[1]`..`[5]` citation badges**. If the catalog lacks supporting evidence, displays an honest *"Insufficient supporting publications"* notice without inventing facts.
    - **Right Sticky Pane (`Supporting Publications & Evidence`)**: Displays *"These 5 publications were used to prepare your answer"*, highlights whichever citation badge you click, shows the exact **quoted passage** from each paper's abstract, and provides direct `Inspect Publication` and `Original Source` links.
- **Behind-the-Scenes Technology (Subsystem F8 — Grounded RAG)**:
  - `POST /api/assistant/ask` (`research_assistant/rag_engine.py`) runs Hybrid Top-K retrieval, sentence-level semantic + lexical passage scoring, and a strict **domain-grounding sufficiency guardrail** (refusing out-of-scope queries with 0 citations).
  - If a local **Ollama** server (`OLLAMA_BASE_URL`, e.g., `llama3.2:3b`) is running, it generates a grounded narrative answer; otherwise it runs a deterministic **Extractive Grounded Synthesizer** that quotes and cites only verified retrieved sentences with 100% citation accuracy.

---

### 4.17 Account & Profile Settings (`/settings`)
- **Access**: Signed-in Members
- **File**: `frontend/src/pages/SettingsPage.tsx`
- **What Is on This Page**:
  - Edit Full Name, Department, Academic Biography, Research Interests, comma-separated Research Topics, Personal Website / Lab Page, and external Publication Profile Links (one URL per line).
  - **Followed Research Topics Manager**: Add new topics or remove followed topics (`×`) with instant toast feedback.
- **Behind-the-Scenes Technology**: `PATCH /api/users/me`, `GET /api/users/me/topics`, `POST /api/users/me/topics/follow`, `DELETE /api/users/me/topics/follow/{topic}`. Updating interests immediately updates your Home feed and Recommendation profiles.

---

### 4.18 Institutional Insights — Admin Only (`/analytics`)
- **Access**: **Administrators ONLY** (guarded by `<RequireAdmin>` on frontend & `require_admin` JWT RBAC on backend; returns HTTP `403` for non-admins)
- **File**: `frontend/src/pages/AnalyticsPage.tsx`
- **What Is on This Page**:
  1. **Executive Summary Strip**: Indexed Publications, University Members, Library Saves, Community Discussions, and 6-Month Research Activity.
  2. **Research Activity Over Time** (Stacked AreaChart): Monthly reads, searches, discussions, and library saves.
  3. **Participation by Department** (Grouped BarChart): Side-by-side comparison across all 6 departments.
  4. **Interactive 4-Level Explorer (`University → Department → Topic → Member`)**: Click any department → inspect its leading research topics (spam noise filtered out) → click any topic → inspect contributing members → click any member to view their top topics and saved papers, with clickable breadcrumb navigation!
  5. **Cross-Department Research Overlap**: Pairs of departments sharing co-saved literature.
  6. **University Research Theme Groups**: Automatically grouped clusters of co-occurring research topics.
  7. **Most Saved Publications** & **Most Discussed Research Threads** tables.
  8. **`Refresh Insights` Button**: Re-runs the full Data Warehouse ETL live.
- **Behind-the-Scenes Technology (Subsystem F9 — Data Warehouse & OLAP)**:
  - Powered directly by **DuckDB** executing columnar OLAP SQL queries (`analytics/warehouse_service.py` & `data_warehouse/sql/analytical_queries.sql`) over **9 Apache Parquet Star Schema tables** (`data/parquet/*.parquet`).
  - Theme groups are computed via **Scikit-learn Ward Hierarchical Agglomerative Clustering** (`AgglomerativeClustering`) over department-topic TF-IDF profiles.

---

### 4.19 Administration & Moderation — Admin Only (`/admin`)
- **Access**: **Administrators ONLY**
- **File**: `frontend/src/pages/AdminPage.tsx`
- **What Is on This Page (4 Tabs)**:
  1. **Moderation Alerts**: Review, dismiss, or take action (suspend account) on flagged accounts and emerging topic notices (`GET/PATCH /api/admin/alerts`).
  2. **Flagged Accounts**: View accounts flagged for unusual behavior, inspect plain-language review reasons, click `Run Activity Review` to rescan live, and click `Suspend` / `Reactivate` (`GET /api/admin/spam-report`, `POST /api/admin/users/{id}/toggle-active`).
  3. **Library Updates**: Trigger live incremental external scholarly syncing (`Sync OpenAlex`, `Sync arXiv`, `Sync Research Feeds`) and inspect job history (records checked, new papers added, duplicates merged) (`GET /api/admin/ingestion-jobs`, `POST /api/admin/ingestion/run`).
  4. **System Diagnostics**: Restricted technical benchmark summary showing live executed evaluation metrics for Search, Recommendations, Deduplication, Spam Detection, Trend Detection, and Research Assistant (`GET /api/admin/evaluations`).
- **Behind-the-Scenes Technology (Subsystems F4 & F7)**:
  - **Spam Detection** (`ml/anomaly_detection/spam_detector.py`): Extracts 7 behavioral features per account (hourly burst rate, daily activity intensity, pairwise TF-IDF duplicate text similarity, tag-stuffing count, off-hours 01:00–04:59 ratio, follow velocity, promotional phrase density) and runs **Scikit-learn `IsolationForest`** combined with interpretable behavioral risk rules.
  - **External Data Ingestion** (`ingestion/pipeline.py` & `ingestion/scheduler.py`): Live HTTP ingestion from OpenAlex, arXiv, and curated RSS feeds into Bronze raw JSON (`data/raw/`) + optional MinIO bucket, Silver Parquet (`data/processed/`), and scheduled 12-hour APScheduler background refreshes.

---

## 5. Complete Technology Stack & Architecture Reference

| Layer | Technologies & Libraries | Purpose in the Platform |
|---|---|---|
| **Frontend UI** | React 18, TypeScript 5, Vite 6, Tailwind CSS 3, React Router 6, Lucide React, Recharts | Responsive 19-page SPA, Chanakya University design system, interactive charts, toast & modal UX |
| **Backend API** | Python 3.12/3.14, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, APScheduler | High-speed REST APIs, request validation, ORM persistence, 12-hour scheduled ingestion |
| **Security & Auth** | `bcrypt`, `PyJWT` (HS256), FastAPI `HTTPBearer`, RBAC dependencies | Password hashing, stateless JWT sessions, Student/Faculty/Researcher/Admin route protection |
| **Operational DB (OLTP)** | PostgreSQL 16 + `pgvector` + `pg_trgm` (with zero-setup SQLite local fallback) | 15 normalized relational tables (`users`, `papers`, `posts`, `comments`, `saved_papers`, `saved_posts`, `activity_events`, etc.), GIN FTS & HNSW vector indexing |
| **Data Lake (Bronze/Silver)** | Local Filesystem (`data/raw/`, `data/processed/`) + MinIO S3-compatible storage | Unchanged raw API JSON archival (Bronze) and cleaned Silver Parquet (`papers_silver.parquet`) |
| **Data Warehouse (Gold OLAP)** | **Apache Parquet** (`pyarrow`), **Pandas**, **DuckDB** | Kimball Star Schema (5 Dimensions + 4 Fact Tables) with sub-50ms columnar OLAP queries & 4-level drill-down |
| **External Data Sources** | `httpx`, `feedparser`, XML ElementTree → **OpenAlex API**, **arXiv Atom API**, **Curated RSS** | Real scholarly papers, reconstructed abstracts, citation references, and research feeds |
| **Data Mining & ML** | `scikit-learn`, `scipy`, `numpy`, `NetworkX`, `datasketch`, `mlxtend`, `sentence-transformers` (with 384-d TF-IDF+SVD fallback) | Semantic embeddings, MinHash LSH deduplication, Citation PageRank, Content+CF recommendations, FP-Growth, Louvain/Modularity communities, Isolation Forest, Ward clustering |
| **AI Research Assistant** | Grounded RAG pipeline + local **Ollama** (`llama3.2:3b`) + Extractive Grounded Fallback | Evidence-grounded natural-language Q&A with inline citations & anti-hallucination refusal |
| **Testing & Evaluation** | `pytest`, FastAPI `TestClient`, `matplotlib`, reproducible seed `42` ground truth | Automated API/ML regression suite (11/11 passing) & empirical benchmark charts |
| **Containerization** | Docker, Docker Compose, Nginx reverse proxy | One-command multi-container deployment (`postgres`, `minio`, `backend`, `frontend`) |

---

## 6. Data Engineering, Data Warehouse & Star Schema Guide

### Medallion Lakehouse Flow
1. **Bronze Layer (`data/raw/{openalex,arxiv,rss}/` + MinIO `chanakya-raw-lake`)**: Original external API JSON payloads stored verbatim with UTC timestamps.
2. **Silver Layer (`data/processed/papers_silver.parquet` + Relational OLTP DB)**: Cleaned, normalized titles/DOIs/arXiv IDs/authors, deduplicated canonical papers with provenance (`is_synthetic` flag clearly separating real external records from synthetic supplement), 384-d embeddings, and PageRank scores.
3. **Gold Layer (`data/parquet/*.parquet` → `data_warehouse/duckdb/chanakya_dw.duckdb`)**: Rebuilt via `data_warehouse/etl.py` into a **Kimball Star Schema**:

| Table Name | Role | Verified Rows | Description |
|---|---|---:|---|
| `dim_date` | Dimension | 183 | Calendar days spanning 6 months (year, quarter, month, ISO week, day of week) |
| `dim_department` | Dimension | 6 | Chanakya University departments (`CSAI`, `DSE`, `ECE`, `BIO`, `MGT`, `REM`) |
| `dim_member` | Dimension | 60 | University members with role, department, spam flag & synthetic provenance |
| `dim_topic` | Dimension | 511 | Normalized research topic tags |
| `dim_paper` | Dimension | 687 | Canonical papers with source, year, citations, PageRank & campus saves |
| `fact_research_activity` | Fact | 12,500 | Atomic telemetry grain: 1 row per read, save, search, post, comment, upvote, or follow |
| `fact_paper_saves` | Fact | 686 | Member paper-save transactions for campus library & cross-dept overlap analytics |
| `fact_search_events` | Fact | 2,952 | Search query volume and search mode telemetry |
| `fact_post_engagement` | Fact | 514 | Community post engagement (likes/upvotes & comment counts) |

---

## 7. Data Mining, Machine Learning & RAG Algorithms Explained

| Feature | Algorithm / Method | Library / File | How It Works |
|---|---|---|---|
| **Unified Search** | BM25/TF-IDF + 384-d Cosine Vector Search + Anisotropy-Adjusted RRF (`k=60`) + Citation PageRank | `ml/search/search_engine.py`, `ml/embeddings/embedder.py`, `networkx` | Combines lexical precision with anisotropy-adjusted semantic excess and citation authority across 4 simultaneous result panels. |
| **Duplicate Merging** | Exact DOI/arXiv + Author Initial Canonicalization + MinHash & LSH (128 perms) | `ml/duplicate_detection/deduplicator.py`, `datasketch` | Resolves variants like `"A. Sharma"` vs `"Ananya Sharma"` and punctuation/wording tweaks into one canonical paper listing all sources. |
| **Paper Recommendations** | Content-Based Embedding Similarity + User-Item Collaborative Filtering + Cold-Start | `ml/recommendations/recommender.py`, `scikit-learn`, `numpy` | Matches user interest centroids + similar-library peers; automatically switches to profile + department + popularity blending for new users. |
| **"Also Saved" Papers** | FP-Growth Association Rule Mining (`max_len=2`) + Co-Save Lift | `ml/recommendations/recommender.py`, `mlxtend` | Mines frequent co-saved paper baskets efficiently without candidate blow-up. |
| **Researcher Matching** | Profile Embeddings + Tag Jaccard + 2-Hop Graph + Greedy Modularity Communities | `ml/recommendations/recommender.py`, `networkx` | Detects campus research clusters across follow & co-save graphs to recommend collaborators. |
| **Emerging Topics** | Non-Adjacent, Outlier-Guarded Sliding-Window Z-Score with Poisson Variance Floor | `ml/trend_detection/trends.py`, `numpy` | Detects genuine sudden surges (`Z >= 3.0`) without adjacent-week boundary contamination while excluding spam accounts. |
| **Spam & Abuse Review** | 7 Behavioral Features + Unsupervised Isolation Forest + Risk Rules | `ml/anomaly_detection/spam_detector.py`, `scikit-learn` | Catches bursty, duplicate-content, tag-stuffing, off-hours bot accounts with human-readable reasons. |
| **Topic Clustering** | Ward Linkage Hierarchical Agglomerative Clustering | `analytics/warehouse_service.py`, `scikit-learn` | Groups related university topics by cross-department activity profiles. |
| **Research Assistant** | Hybrid Passage Retrieval + Sufficiency Guardrail + Ollama / Extractive Synthesis | `research_assistant/rag_engine.py`, `httpx` | Produces verifiable `[1]..[K]` citations and refuses out-of-scope questions rather than hallucinating. |

---

## 8. Verified Dataset Counts & Executed Evaluation Benchmarks

### Dataset Counts (Docker PostgreSQL + DuckDB, Fixed Seed = `42`)
- **Papers**: **687** total (**546 real external papers**: 389 OpenAlex, 127 arXiv, 30 RSS + 141 synthetic) · **224** in shared Chanakya Library (`686` saves) · **1,950** citation edges.
- **Members & Departments**: **60** members across **6** departments (including 6 planted spam accounts in ground truth) · **629** follow relationships.
- **Community & Activity**: **2,553** posts & comments combined (514 posts + 2,039 comments/replies) · **12,500** activity events spanning **183 days** (6 months).

### Executed ML Evaluation Results (`docker compose exec backend python evaluation/run_evaluations.py`)

| Subsystem | Baseline vs Intelligent Method | Actual Executed Metrics |
|---|---|---|
| **Search (12 queries, 687 papers vs frozen 560-paper qrels)** | Keyword vs Semantic vs **Hybrid (RRF+PageRank)** | Keyword NDCG@10=`0.4518` (P@5=`0.4333`) · Semantic P@5=`0.5500` (NDCG@10=`0.4677`) · **Hybrid P@5=`0.5000`, NDCG@10=`0.4752` (Highest)** |
| **Recommendations (35 users)** | Popularity Baseline vs **Hybrid Content+CF** | Baseline P@5=`0.0971`, R@10=`0.1752` → **Hybrid P@5=`0.1829` (1.88×), R@10=`0.5057` (2.89×)** |
| **Duplicate Detection (36 planted pairs)** | Exact Match vs **MinHash LSH + Author ER** | Baseline F1=`0.0541` (1/36 TP) → **MinHash LSH + ER F1=`1.0000` (36/36 TP, 0 FP)** |
| **Spam Detection (6 planted bots)** | Volume Threshold vs **Isolation Forest + Rules** | Baseline F1=`0.7059` (5 FP) → **Isolation Forest F1=`1.0000` (6/6 TP, 0 FP)** |
| **Topic Spike Detection (3 planted)** | **Non-Adjacent Outlier-Guarded Z-Score** | **Detection Rate=`1.0000` (3/3), Precision=`1.0000`, False Alarms=`0`** |
| **Research Assistant (6 queries)** | **Grounded RAG Pipeline** | **Hit@5=`1.0000`, Citation Acc=`1.0000`, Coverage=`1.0000`, Out-of-Scope Refusal=`1.0000`** |

---

## 9. Running Locally, Docker Compose & Troubleshooting

### Option A: Local Execution on Windows
```powershell
cd <project-root>

# Start both Backend (8000) & Frontend (5173):
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1

# Re-run full ingestion, synthetic data, embeddings, PageRank, DuckDB warehouse, charts, evaluations & Pytest:
powershell -ExecutionPolicy Bypass -File scripts\regenerate_all.ps1
```

### Option B: Docker Compose (PostgreSQL + MinIO + FastAPI + Nginx)
Start Docker Desktop, then run:
```powershell
cd <project-root>
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec backend python scripts/bootstrap_all.py
docker compose exec backend python evaluation/run_evaluations.py
```

### Quick Troubleshooting
- **Port 8000 or 5173 already in use**: Stop any existing `uvicorn` or `node` processes before re-running `scripts\start_local.ps1`.
- **Admin pages redirect to `/dashboard`**: Sign out and sign in using the Administrator account (`admin@chanakya.edu.in` / `Chanakya@2026`).
- **Want local generative LLM answers in Research Assistant**: Install [Ollama](https://ollama.com/), run `ollama pull llama3.2:3b`, and the Research Assistant will automatically switch from extractive synthesis to Ollama while preserving all citation and refusal guardrails.
