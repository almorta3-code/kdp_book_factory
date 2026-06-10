# KDP Activity Book Factory

## Vision
Build a production-grade AI-powered KDP Activity Book Generator that creates:
- Children's activity workbooks
- Coloring books
- Educational workbooks
- KDP upload packages
- Etsy printable packages

Core principle:
Generate assets separately (text, images, activities) and assemble with Python. Never generate full worksheet pages as a single AI image.

---

# Recommended Models

- Planner / Strategy: GPT-5.5
- Content Generation: GPT-5.4-mini
- Images: GPT-Image-2
- Structured Outputs: Enabled everywhere

---

# Core Modules

1. Niche Research
2. Book Blueprint Generator
3. Content Generator
4. Activity Generator
5. Image Generator
6. PDF Layout Engine
7. Quality Control
8. KDP Upload Package Generator

---

# Codex Prompt 1 â€” Project Setup

You are building a production-quality Python app called KDP Activity Book Factory.

Goal:
Create a local web app that generates complete KDP-ready children's activity workbooks using Google Gemini API.

Tech stack:
- Python 3.11+
- Streamlit frontend
- FastAPI-style modular backend structure if needed
- Google Gemini API
- Pydantic models
- ReportLab for PDF layout
- Pillow for image processing
- SVG/Python logic for mazes, word searches, dot-to-dot
- Local file storage in /outputs

Create the project structure:

kdp_book_factory/
  app.py
  requirements.txt
  .env.example
  README.md
  src/
    config.py
    google_client.py
    schemas/
    generators/
    layout/
    activities/
    quality/
    export/
    utils/
  outputs/
  templates/
  tests/

Requirements:
1. Add environment loading for GOOGLE_API_KEY.
2. Add settings for model_text_planner, model_text_fast, model_image.
3. Default models:
   - planner: gpt-5.5
   - fast_text: gpt-5.4-mini
   - image: gpt-image-2
4. Build a Streamlit page with fields:
   - book theme
   - age range
   - trim size
   - number of pages
   - color mode
   - activity types
   - style direction
5. Add a â€œGenerate Book Blueprintâ€ button.
6. No fake final generation yet. Just setup clean architecture.
7. Add clear comments.
8. Make the app run with: streamlit run app.py

---

# Codex Prompt 2 â€” Data Schemas

Add Pydantic schemas for the full book system.

Create schemas for:

BookRequest
BookBlueprint
PageSpec
AnimalUnit
KDPMetadata

Use strict validation.
Add example JSON files in /templates/examples.

---

# Codex Prompt 3 â€” Blueprint Generator

Create src/generators/blueprint_generator.py.

Function:
generate_book_blueprint(request: BookRequest) -> BookBlueprint

Use Gemini structured outputs with the planner model.

The prompt should make the model act as:
- KDP niche strategist
- children's educational book designer
- activity workbook expert

Must generate:
- title
- subtitle
- audience
- unique angle
- page-by-page plan
- activity mix
- KDP positioning

Save blueprint.json.

---

# Codex Prompt 4 â€” Content Generator

Create src/generators/content_generator.py.

Function:
generate_content_units(blueprint: BookBlueprint)

Generate:
- short stories
- facts
- vocabulary
- quizzes
- matching pairs
- tracing words
- flashcards
- image prompts
- coloring prompts

Save content_units.json.

---

# Codex Prompt 5 â€” Activity Logic

Create:

- word_search.py
- maze.py
- dot_to_dot.py
- matching.py
- tracing.py
- quiz.py

Generate real structured activity data.
Include answer keys.
Add tests.

---

# Codex Prompt 6 â€” Image Generator

Create image_generator.py

Functions:
- generate_character_image()
- generate_cover_image()
- generate_coloring_page()
- generate_icon()

Use GPT-Image-2.

Rules:
- No readable text inside images.
- PNG outputs.
- Retry logic.
- Placeholder mode.
- Consistent style builder.

---

# Codex Prompt 7 â€” PDF Layout Engine

Create pdf_builder.py using ReportLab and Pillow.

Requirements:
- 8.5x11 support
- 300 DPI
- safe margins
- title pages
- story pages
- flashcards
- activities
- coloring pages
- answer keys
- certificate pages

Output:
interior.pdf

---

# Codex Prompt 8 â€” KDP Package Export

Generate:
- cover_prompt.txt
- cover.png
- cover.pdf
- interior.pdf
- metadata.json
- amazon_listing.txt
- keywords.txt
- categories.txt
- social_posts.txt
- etsy_description.txt

Zip everything into:
kdp_upload_package.zip

---

# Codex Prompt 9 â€” Quality Control

Create qc_checker.py

Checks:
- page count
- image resolution
- duplicate content
- answer keys
- copyrighted characters
- trademark references
- missing assets
- PDF validity

Generate:
qc_report.md

---

# Codex Prompt 10 â€” Final Polish

Add:
- sidebar workflow
- save/load projects
- progress bars
- error handling
- sample project
- complete README

Workflow:
1. Project Setup
2. Generate Blueprint
3. Generate Content
4. Generate Activities
5. Generate Images
6. Build PDF
7. Run QC
8. Export Package

---

# Success Strategy

Do NOT compete with basic coloring books.

Target:
- Activity Workbooks
- Educational Workbooks
- Homeschool Resources
- Teacher Resources
- Printable Etsy Bundles

Create a series:
- Desert Animals
- Ocean Animals
- Jungle Animals
- Farm Animals
- Dinosaurs
- Space
- Insects
- Unicorns
- Vehicles

Build a brand, not a single book.

