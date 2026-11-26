# REST API Documentation — Chanakya Research Commons

Base URL (Local): `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`  
Authentication: Bearer JWT (`Authorization: Bearer <access_token>`)

---

## Health & Reference
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | API health status and active database backend (`postgresql` or `sqlite`). |
| `GET` | `/api/departments` | Public | List all 6 Chanakya University departments with active member counts. |
| `GET` | `/api/dashboard/summary` | Optional | Platform KPI summary and personalized user stats if signed in. |

## F1 — Accounts, Profiles & Following
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register a new university member (`student`, `faculty`, or `researcher` only; `admin` self-registration is rejected with HTTP 422/403). Returns JWT + user profile. |
| `POST` | `/api/auth/login` | Public | Authenticate via email or username + bcrypt-verified password. Returns JWT + user profile. |
| `POST` | `/api/auth/logout` | User | Confirm session sign-out. |
| `GET` | `/api/auth/me` | User | Get current authenticated member's profile and stats. |
| `PATCH` | `/api/users/me` | User | Update name, department, bio, research interests, research tags, publication links, and personal website. |
| `GET` | `/api/users` | Optional | Researcher directory filterable by `q`, `department_code`, `role`, `tag`. |
| `GET` | `/api/users/{user_id}` | Optional | Detailed member profile with followers/following counts, recent posts, and recently saved papers. |
| `POST` / `DELETE` | `/api/users/{user_id}/follow` | User | Follow or unfollow another university member. |
| `GET` / `POST` / `DELETE` | `/api/users/me/topics` & `/follow` | User | List, follow, or unfollow research topics/tags. |

## F2 — Posts & Discussions
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/posts` | Optional | List discussions with `feed=all|personalized|following|topics`, `tag`, `author_id`, `paper_id`. |
| `POST` | `/api/posts` | User | Create a discussion post with tags and optional attached library paper or URL. |
| `GET` | `/api/posts/{post_id}` | Optional | Fetch full post detail along with comments and nested replies. |
| `PATCH` / `DELETE` | `/api/posts/{post_id}` | Author/Admin | Edit or delete a post. |
| `POST` | `/api/posts/{post_id}/comments` | User | Add a top-level comment or nested reply (`parent_comment_id`). |
| `POST` | `/api/posts/{post_id}/upvote` | User | Toggle upvote / remove upvote on a post. |
| `POST` | `/api/posts/{post_id}/save` | User | Bookmark / unbookmark a discussion post (`saved_posts`). |

## F3 — Shared University Library & Personal Collections
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/papers` | Optional | Browse all papers or shared university library (`only_library=true`), filter by `source`, `department`, `topic`, `year_from`, `sort=saves|citations|pagerank|recent`. |
| `GET` | `/api/papers/{paper_id}` | Optional | Paper details, logs a `view` telemetry event, returns campus savers, related posts, and **FP-Growth "also saved"** recommendations. |
| `POST` | `/api/papers/add-by-identifier` | User | Add a paper by DOI, arXiv ID, or URL; auto-fetches live metadata from OpenAlex/arXiv, deduplicates, embeds, and saves to campus library. |
| `POST` / `PATCH` / `DELETE` | `/api/library/save` (`/{paper_id}`) | User | Save paper, edit private notes / collection assignment, or unsave paper (updates campus `save_count`). |
| `GET` | `/api/library/my` | User | Get current user's saved papers (optionally filtered by `collection_id`) including private notes. |
| `GET` / `POST` / `PATCH` / `DELETE` | `/api/collections` (`/{id}`) | User | Manage personal research paper collections. |

## F4–F9 — Unified Search, Recommendations, Trends, RAG, Analytics & Admin
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/search/unified` | Optional | **F5 Unified 4-Panel Search** (`q`, `mode=hybrid|keyword|semantic`, `department`, `year_from`, `year_to`, `source`, `tag`). Logs search telemetry. |
| `GET` | `/api/recommendations/papers` | User | **F6 Personalized Paper Recommendations** (Hybrid Content+CF or Cold-Start). |
| `GET` | `/api/recommendations/researchers` | User | **F6 Researcher Recommendations** with NetworkX community detection. |
| `GET` | `/api/recommendations/also-saved/{paper_id}` | Public | **F6 FP-Growth** "Members who saved this also saved" association rules. |
| `GET` | `/api/trends` | Public | **F7 Trending Topics**, weekly series, and sudden Z-score topic spike alerts. |
| `POST` | `/api/assistant/ask` | Optional | **F8 Grounded RAG Research Assistant** returning answer, inline citations, and retrieved passages. |
| `GET` | `/api/analytics/overview` | **Admin** | **F9 DuckDB Star Schema Overview** (KPIs, monthly trends, dept comparisons, cross-dept collaboration, Ward topic clusters). |
| `GET` | `/api/analytics/drilldown` | **Admin** | **F9 4-Level OLAP Drill-Down** (`department_code`, `topic_name`, `member_id`). |
| `POST` | `/api/analytics/rebuild-warehouse` | **Admin** | Trigger immediate Parquet Star Schema + DuckDB ETL refresh. |
| `GET` / `PATCH` | `/api/admin/alerts` (`/{id}`) | **Admin** | List and review/dismiss/action F7 spam & topic spike alerts. |
| `GET` | `/api/admin/spam-report` | **Admin** | Run/view Isolation Forest + behavioral spam account report (`rescan=true` to persist new alerts). |
| `POST` | `/api/admin/users/{user_id}/toggle-active` | **Admin** | Suspend or reactivate a flagged user account. |
| `PATCH` | `/api/admin/users/{user_id}/role` | **Admin** | Promote or update a member's role (`student`, `faculty`, `researcher`, `admin`). |
| `GET` / `POST` | `/api/admin/ingestion-jobs` & `/ingestion/run` | **Admin** | View F4 ingestion history and trigger live incremental OpenAlex / arXiv / RSS ingestion. |
| `GET` | `/api/admin/evaluations` | **Admin** | Fetch the latest executed ML evaluation metrics JSON. |
