# KDP Activity Book Factory

A local Streamlit app for creating children's KDP activity workbook packages with Google Gemini, structured planning, activity generators, image assets, PDF layout, quality checks, and export files.

The app is designed for a non-coder workflow: open it, follow the sidebar steps, save your project, and export a ready-to-review upload package.

## Install

Open PowerShell on the computer where Python works, then run:

```powershell
cd kdp_book_factory
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Add API Key

Create a Google AI Studio key at <https://aistudio.google.com/apikey>, then open `.env` and add it:

```text
GOOGLE_API_KEY=your-google-ai-studio-key-here
MODEL_TEXT_PLANNER=gemini-3.5-flash
MODEL_TEXT_FAST=gemini-3.5-flash
MODEL_IMAGE=gemini-3.1-flash-image
```

The app can still make placeholder images without image API calls, but blueprint, content, and metadata generation need the API key.

## Run App

```powershell
streamlit run app.py
```

Your browser will open the local app.

## Generate Your First Book

Use the left sidebar workflow:

1. **Dashboard**: View KPIs, charts, projects, brands, books, languages, and exports.
2. **Research Center**: Test one niche idea or rank several niches against each other before building the book.
3. **Brand Builder**: Create a reusable long-term publishing brand.
4. **Character Manager**: Create reusable mascot prompts for consistent characters across many books.
5. **Style Library**: Save reusable illustration styles for future books.
6. **Translation Center**: Translate stories, facts, quizzes, flashcards, and tracing words.
7. **Project Setup**: Enter the theme, age range, page count, trim size, activity types, and style direction.
8. **Generate Blueprint**: Create the full page-by-page book plan.
9. **Generate Content**: Create animal/topic stories, facts, vocabulary, quiz content, tracing words, and prompts.
10. **Generate Activities**: Build drawable data for mazes, word searches, dot-to-dot, matching, tracing, and quiz pages.
11. **Cover Lab**: Generate 10 ranked cover concepts and choose one before creating cover art.
12. **Generate Images**: Create PNG assets. Keep placeholder mode on while testing.
13. **Build PDF**: Export `interior.pdf`.
14. **Run QC**: Generate `qc_report.md` with pass, warning, and fail checks.
15. **Export Package**: Create the KDP upload folder and zip file.
16. **Etsy Export**: Create printable Etsy products and a zip bundle.
17. **Teacher Resources**: Create a K-5 teacher pack with lesson plans, discussion questions, worksheets, activities, and assessments.
18. **Homeschool Center**: Convert the workbook into a parent-friendly homeschool product.
19. **Marketing Center**: Generate Amazon, blog, Pinterest, TikTok, YouTube Shorts, Facebook, and email launch assets.
20. **Compliance Center**: Generate provenance files, ownership reports, scans, hashes, and an evidence package.

Research results are saved in:

```text
outputs/research/
```

The opportunity ranking tool can compare ideas such as `Desert Animals`, `Space`, `Dinosaurs`, and `Farm Animals`, then export the ranked table as CSV.

Brand profiles are saved in:

```text
projects/brands/
```

Mascot character profiles are saved as `character_profile.json` under:

```text
projects/brands/characters/
```

Illustration styles are saved as JSON under:

```text
projects/styles/
```

Language packs are saved in the current project under:

```text
outputs/current_project/language_packs/
```

Cover Lab saves concept planning files in the current project:

```text
outputs/current_project/cover_concepts.json
outputs/current_project/selected_cover_concept.json
```

Compliance evidence is saved in the current project:

```text
outputs/current_project/provenance/
outputs/current_project/compliance/
outputs/current_project/compliance_package.zip
```

The KDP upload package also includes a `/compliance/` folder when exported.

You can also click **Load Desert Animals Sample** in the sidebar to try the workflow with a ready-made sample project.

## Save And Load Projects

The app works in:

```text
outputs/current_project/
```

Use the sidebar to save the current project into:

```text
outputs/projects/
```

Later, choose a saved project in the sidebar and load it back into the active workspace.

## Upload Package

The final export creates:

```text
outputs/current_project/kdp_upload_package/
outputs/current_project/kdp_upload_package.zip
```

The package contains:

- `cover_prompt.txt`: prompt/direction for final cover art
- `cover.png`: generated or placeholder cover image
- `cover.pdf`: placeholder cover PDF for review only
- `interior.pdf`: workbook interior PDF
- `metadata.json`: structured KDP metadata
- `amazon_listing.txt`: title, subtitle, description, keywords, categories, and checklist
- `keywords.txt`: seven keyword phrases
- `categories.txt`: two category suggestions
- `social_posts.txt`: simple launch posts
- `etsy_description.txt`: optional marketplace description

The Etsy export creates:

```text
outputs/current_project/etsy_bundle/
outputs/current_project/etsy_bundle.zip
```

It includes printable flashcards, posters, reward charts, certificates, worksheet packs, printable coloring pages when assets exist, and Etsy listing helper files.

The Teacher Resources export creates:

```text
outputs/current_project/teacher_pack/
outputs/current_project/teacher_pack.zip
```

It includes `teacher_pack.pdf` for classroom use and `teacher_pack.json` for structured reuse.

The Homeschool Center export creates:

```text
outputs/current_project/homeschool_pack/
outputs/current_project/homeschool_pack.zip
```

It includes `homeschool_pack.pdf` with weekly plans, learning objectives, daily activities, a parent guide, and a progress tracker.

Marketing assets are saved in:

```text
outputs/marketing/
```

Each marketing export includes structured JSON plus a readable summary file with Amazon listing assets, SEO articles, social ideas, short video scripts, and an email launch sequence.

Before uploading to KDP, review the PDF, run QC, check KDP's current cover-size calculator, and order a proof copy.

## Project Structure

```text
kdp_book_factory/
  app.py
  requirements.txt
  .env.example
  README.md
  src/
    activities/
    branding/
    compliance/
    covers/
    dashboard/
    education/
    export/
    generators/
    layout/
    localization/
    marketing/
    quality/
    research/
    schemas/
    utils/
  outputs/
  templates/examples/
  tests/
```
