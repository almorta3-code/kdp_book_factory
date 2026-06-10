from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.branding.brand_builder import BrandProfile, build_brand_profile, save_brand_profile
from src.branding.character_engine import CharacterProfile, build_character_profile, save_character_profile
from src.branding.style_library import IllustrationStyle, load_styles, save_style
from src.compliance.provenance_engine import (
    export_compliance_package,
    generate_ownership_report,
    hash_project_files,
    record_output_file,
    register_brand,
    register_character,
    run_copyright_scan,
    run_trademark_scan,
)
from src.config import get_settings
from src.covers.cover_intelligence import CoverConcept, CoverConceptSet, generate_cover_concepts
from src.dashboard.publishing_dashboard import DashboardData, collect_dashboard_data
from src.education.homeschool_generator import export_homeschool_pack
from src.education.teacher_resource_generator import export_teacher_pack
from src.export.etsy_bundle_generator import export_etsy_bundle
from src.export.kdp_package import export_kdp_upload_package
from src.generators.activity_generator import generate_and_save_activity_data
from src.generators.blueprint_generator import generate_book_blueprint
from src.generators.content_generator import generate_content_units, save_content_units
from src.generators.image_generator import (
    generate_character_image,
    generate_coloring_page,
    generate_cover_image,
    generate_icon,
)
from src.layout.pdf_builder import build_interior_pdf
from src.localization.multilanguage_engine import SUPPORTED_LANGUAGES, LanguagePack, save_language_pack, translate_project
from src.marketing.marketing_engine import MarketingAssets, export_marketing_assets
from src.quality.qc_checker import QCItem, run_quality_checks
from src.research.niche_research_engine import NicheResearchResult, analyze_niche, save_niche_research_result
from src.research.opportunity_engine import OpportunityScore, rank_opportunities, save_opportunity_scores
from src.schemas.book import AnimalUnit, BookBlueprint, BookRequest, ContentUnitBatch
from src.utils.project_store import (
    current_project_dir,
    list_saved_projects,
    load_sample_project,
    load_saved_project,
    save_current_project,
)


WORKFLOW_STEPS = [
    "Dashboard",
    "Research Center",
    "Brand Builder",
    "Character Manager",
    "Style Library",
    "Translation Center",
    "1. Project Setup",
    "2. Generate Blueprint",
    "3. Generate Content",
    "4. Generate Activities",
    "Cover Lab",
    "5. Generate Images",
    "6. Build PDF",
    "7. Run QC",
    "8. Export Package",
    "Etsy Export",
    "Teacher Resources",
    "Homeschool Center",
    "Marketing Center",
    "Compliance Center",
]

SAMPLE_PROJECT_DIR = Path(__file__).resolve().parent / "templates" / "examples" / "desert_animals_project"
BRANDS_DIR = Path(__file__).resolve().parent / "projects" / "brands"


st.set_page_config(page_title="KDP Activity Book Factory", layout="wide")


def project_file(filename: str) -> Path:
    return current_project_dir() / filename


def save_request(request: BookRequest) -> Path:
    path = project_file("request.json")
    path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    st.session_state["current_request"] = request.model_dump_json()
    try:
        record_output_file(path)
    except Exception:
        pass
    return path


def save_blueprint(blueprint: BookBlueprint) -> Path:
    path = project_file("blueprint.json")
    path.write_text(blueprint.model_dump_json(indent=2), encoding="utf-8")
    st.session_state["current_blueprint"] = blueprint.model_dump_json()
    try:
        record_output_file(path)
    except Exception:
        pass
    return path


def load_request() -> BookRequest | None:
    cached = st.session_state.get("current_request")
    if cached:
        return BookRequest.model_validate_json(cached)
    path = project_file("request.json")
    if not path.exists():
        return None
    return BookRequest.model_validate_json(path.read_text(encoding="utf-8"))


def load_blueprint() -> BookBlueprint | None:
    cached = st.session_state.get("current_blueprint")
    if cached:
        return BookBlueprint.model_validate_json(cached)
    path = project_file("blueprint.json")
    if not path.exists():
        return None
    return BookBlueprint.model_validate_json(path.read_text(encoding="utf-8"))


def list_brand_profile_files() -> list[Path]:
    if not BRANDS_DIR.exists():
        return []
    return sorted(BRANDS_DIR.glob("*.json"), reverse=True)


def load_brand_profile(path: Path) -> BrandProfile:
    return BrandProfile.model_validate_json(path.read_text(encoding="utf-8"))


def load_content_units() -> list[AnimalUnit]:
    cached = st.session_state.get("current_content_units")
    if cached:
        return ContentUnitBatch.model_validate_json(cached).units
    path = project_file("content_units.json")
    if not path.exists():
        return []
    return ContentUnitBatch.model_validate_json(path.read_text(encoding="utf-8")).units


def save_cover_concepts(concepts: CoverConceptSet) -> Path:
    path = project_file("cover_concepts.json")
    path.write_text(concepts.model_dump_json(indent=2), encoding="utf-8")
    st.session_state["current_cover_concepts"] = concepts.model_dump_json()
    try:
        record_output_file(path)
    except Exception:
        pass
    return path


def load_cover_concepts() -> CoverConceptSet | None:
    cached = st.session_state.get("current_cover_concepts")
    if cached:
        return CoverConceptSet.model_validate_json(cached)
    path = project_file("cover_concepts.json")
    if not path.exists():
        return None
    return CoverConceptSet.model_validate_json(path.read_text(encoding="utf-8"))


def save_selected_cover_concept(concept: CoverConcept) -> Path:
    path = project_file("selected_cover_concept.json")
    path.write_text(concept.model_dump_json(indent=2), encoding="utf-8")
    st.session_state["selected_cover_concept"] = concept.model_dump_json()
    try:
        record_output_file(path)
    except Exception:
        pass
    return path


def load_selected_cover_concept() -> CoverConcept | None:
    cached = st.session_state.get("selected_cover_concept")
    if cached:
        return CoverConcept.model_validate_json(cached)
    path = project_file("selected_cover_concept.json")
    if not path.exists():
        return None
    return CoverConcept.model_validate_json(path.read_text(encoding="utf-8"))


def load_activity_data() -> dict[str, object]:
    path = project_file("activity_data.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def project_status() -> dict[str, bool]:
    project_dir = current_project_dir()
    return {
        "Setup": (project_dir / "request.json").exists(),
        "Blueprint": (project_dir / "blueprint.json").exists(),
        "Content": (project_dir / "content_units.json").exists(),
        "Activities": (project_dir / "activity_data.json").exists(),
        "Images": (project_dir / "assets" / "cover.png").exists(),
        "PDF": (project_dir / "interior.pdf").exists(),
        "QC": (project_dir / "qc_report.md").exists(),
        "Package": (project_dir / "kdp_upload_package.zip").exists(),
    }


def render_sidebar() -> str:
    settings = get_settings()
    st.sidebar.title("Workflow")
    step = st.sidebar.radio("Choose a step", WORKFLOW_STEPS, label_visibility="collapsed")

    status = project_status()
    complete_count = sum(status.values())
    st.sidebar.progress(complete_count / len(status))
    st.sidebar.caption(f"{complete_count} of {len(status)} steps complete")

    for label, complete in status.items():
        if complete:
            st.sidebar.success(label)
        else:
            st.sidebar.warning(label)

    st.sidebar.divider()
    st.sidebar.subheader("Project")
    project_name = st.sidebar.text_input("Save as", value=st.session_state.get("project_name", "Desert Animals Workbook"))
    st.session_state["project_name"] = project_name

    if st.sidebar.button("Save Current Project"):
        try:
            saved_path = save_current_project(project_name)
            st.sidebar.success(f"Saved: {saved_path.name}")
        except Exception as exc:
            st.sidebar.error(f"Could not save project: {exc}")

    saved_projects = list_saved_projects()
    if saved_projects:
        selected_project = st.sidebar.selectbox("Load saved project", saved_projects)
        if st.sidebar.button("Load Selected Project"):
            try:
                load_saved_project(selected_project)
                st.session_state.clear()
                st.sidebar.success("Project loaded")
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"Could not load project: {exc}")

    if st.sidebar.button("Load Desert Animals Sample"):
        try:
            load_sample_project(SAMPLE_PROJECT_DIR)
            st.session_state.clear()
            st.session_state["project_name"] = "Desert Animals Workbook"
            st.sidebar.success("Sample loaded")
            st.rerun()
        except Exception as exc:
            st.sidebar.error(f"Could not load sample: {exc}")

    st.sidebar.divider()
    st.sidebar.subheader("Runtime")
    st.sidebar.caption(f"Planner: {settings.model_text_planner}")
    st.sidebar.caption(f"Fast text: {settings.model_text_fast}")
    st.sidebar.caption(f"Image: {settings.model_image}")
    if settings.google_api_key:
        st.sidebar.success("API key loaded")
    else:
        st.sidebar.warning("API key missing")

    return step


def render_research_result(result: NicheResearchResult, output_path: Path | None = None) -> None:
    """Display niche research in a plain decision-friendly format."""
    if output_path:
        st.success(f"Research saved to {output_path.as_posix()}")

    st.subheader(result.niche_name)
    st.write(result.audience)
    st.info(result.recommendation)

    scores = [
        {"Area": "Educational value", "Score": result.educational_value_score},
        {"Area": "Evergreen demand", "Score": result.evergreen_score},
        {"Area": "Seasonality", "Score": result.seasonality_score},
        {"Area": "Series potential", "Score": result.series_potential_score},
        {"Area": "Monetization", "Score": result.monetization_score},
    ]

    left, right = st.columns([1, 2])
    with left:
        st.metric("Overall Score", f"{result.overall_score}/100")
        st.write(f"Competition: {result.competition_estimate}")
    with right:
        st.dataframe(scores, use_container_width=True, hide_index=True)

    st.markdown("**Search Intent**")
    st.write(result.search_intent)

    strengths_col, weaknesses_col = st.columns(2)
    with strengths_col:
        st.markdown("**Strengths**")
        for item in result.strengths:
            st.success(item)
    with weaknesses_col:
        st.markdown("**Weaknesses**")
        for item in result.weaknesses:
            st.warning(item)

    st.markdown("**Reasoning**")
    st.write(result.reasoning)


def render_brand_profile(profile: BrandProfile, output_path: Path | None = None) -> None:
    """Display a long-term brand profile in a readable format."""
    if output_path:
        st.success(f"Brand saved to {output_path.as_posix()}")

    st.subheader(profile.brand_name)
    st.info(profile.slogan)

    left, right = st.columns(2)
    with left:
        st.markdown("**Visual Identity**")
        st.write(profile.visual_identity)
        st.markdown("**Color Palette**")
        for color in profile.color_palette:
            st.write(f"- {color}")
    with right:
        st.markdown("**Mascot Concept**")
        st.write(profile.mascot_concept)
        st.markdown("**Publishing Strategy**")
        st.write(profile.publishing_strategy)

    st.markdown("**Future Series**")
    for series in profile.future_series:
        st.write(f"- {series}")


def render_character_profile(profile: CharacterProfile, output_path: Path | None = None) -> None:
    """Display reusable mascot details and prompt set."""
    if output_path:
        st.success(f"Character profile saved to {output_path.as_posix()}")

    st.subheader(profile.name)
    st.caption(f"{profile.species} | {profile.age_appearance}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Personality**")
        st.write(profile.personality)
        st.markdown("**Visual Traits**")
        st.write(profile.visual_traits)
        st.markdown("**Clothing**")
        st.write(profile.clothing)
    with right:
        st.markdown("**Accessories**")
        st.write(profile.accessories)
        st.markdown("**Reusable Prompt Template**")
        st.code(profile.prompt_template, language="text")

    st.markdown("**Pose and Emotion Prompts**")
    prompt_rows = [
        {"Prompt": "Front pose", "Text": profile.front_pose_prompt},
        {"Prompt": "Side pose", "Text": profile.side_pose_prompt},
        {"Prompt": "Happy", "Text": profile.happy_prompt},
        {"Prompt": "Sad", "Text": profile.sad_prompt},
        {"Prompt": "Excited", "Text": profile.excited_prompt},
        {"Prompt": "Teaching", "Text": profile.teaching_prompt},
    ]
    st.dataframe(prompt_rows, use_container_width=True, hide_index=True)


def render_style(style: IllustrationStyle) -> None:
    """Display one reusable illustration style."""
    with st.expander(style.style_name):
        st.markdown("**Image Prompt Modifiers**")
        st.write(style.image_prompt_modifiers)
        st.markdown("**Cover Modifiers**")
        st.write(style.cover_modifiers)
        st.markdown("**Coloring Page Modifiers**")
        st.write(style.coloring_page_modifiers)
        st.markdown("**Icon Modifiers**")
        st.write(style.icon_modifiers)


def render_language_pack(pack: LanguagePack, output_path: Path) -> None:
    """Display a saved language pack summary."""
    with st.expander(f"{pack.language} - {output_path.name}"):
        st.success(f"Saved to {output_path.as_posix()}")
        st.markdown("**Translated Title**")
        st.write(pack.translated_title)
        st.markdown("**Translated Subtitle**")
        st.write(pack.translated_subtitle)
        st.markdown("**Age Notes**")
        st.write(pack.age_appropriateness_notes)
        st.markdown("**Units**")
        st.dataframe(
            [
                {
                    "Original": unit.original_name,
                    "Translated": unit.translated_name,
                    "Tracing Words": ", ".join(unit.tracing_words),
                }
                for unit in pack.units
            ],
            use_container_width=True,
            hide_index=True,
        )


def opportunity_rows(scores: list[OpportunityScore]) -> list[dict[str, object]]:
    """Convert opportunity scores into table-friendly rows."""
    return [
        {
            "Rank": index,
            "Niche": score.niche_name,
            "Total Score": score.total_score,
            "Risk Score": score.risk_score,
            "Saturation": score.saturation_estimate,
            "Expansion Score": score.content_expansion_score,
            "Reasoning": score.reasoning,
        }
        for index, score in enumerate(scores, start=1)
    ]


def render_opportunity_scores(scores: list[OpportunityScore], csv_path: Path | None = None) -> None:
    """Display ranked opportunities as a sortable table and chart."""
    if csv_path:
        st.success(f"CSV saved to {csv_path.as_posix()}")

    rows = opportunity_rows(scores)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.bar_chart(rows, x="Niche", y=["Total Score", "Expansion Score", "Risk Score"])

    if csv_path and csv_path.exists():
        st.download_button(
            "Download CSV",
            data=csv_path.read_text(encoding="utf-8"),
            file_name=csv_path.name,
            mime="text/csv",
        )


def progress_action(label: str, steps: int = 3):
    progress = st.progress(0, text=label)

    def update(current_step: int, text: str) -> None:
        progress.progress(current_step / steps, text=text)

    return update


def page_research_center() -> None:
    st.header("Research Center")
    st.write("Check workbook niches before building a book.")

    tabs = st.tabs(["Analyze One Niche", "Rank Multiple Niches"])

    with tabs[0]:
        niche_idea = st.text_input(
            "Niche idea",
            placeholder="Desert animals activity book for ages 5-7",
        )

        if st.button("Analyze Niche", type="primary"):
            if not get_settings().google_api_key:
                st.error("Add google_api_key in .env before running niche research.")
                return
            try:
                update = progress_action("Analyzing niche", 3)
                update(1, "Reviewing demand and positioning")
                result = analyze_niche(niche_idea)
                update(2, "Saving research")
                output_path = save_niche_research_result(result)
                update(3, "Research ready")
                render_research_result(result, output_path)
            except Exception as exc:
                st.error(f"Niche research failed: {exc}")

    with tabs[1]:
        niche_list = st.text_area(
            "Niche ideas",
            value="Desert Animals\nSpace\nDinosaurs\nFarm Animals",
            help="Enter one niche per line.",
            height=140,
        )

        if st.button("Rank Opportunities", type="primary"):
            if not get_settings().google_api_key:
                st.error("Add google_api_key in .env before ranking opportunities.")
                return
            try:
                niches = [line.strip() for line in niche_list.splitlines() if line.strip()]
                update = progress_action("Ranking opportunities", 3)
                update(1, "Comparing niches")
                scores = rank_opportunities(niches)
                update(2, "Saving CSV")
                csv_path = save_opportunity_scores(scores)
                update(3, "Ranking ready")
                render_opportunity_scores(scores, csv_path)
            except Exception as exc:
                st.error(f"Opportunity ranking failed: {exc}")


def page_brand_builder() -> None:
    st.header("Brand Builder")
    st.write("Create a reusable publishing brand for a long-term workbook series.")

    left, right = st.columns(2)
    with left:
        target_niche = st.text_input(
            "Target niche",
            placeholder="Nature science activity books",
        )
    with right:
        age_range = st.text_input(
            "Age range",
            value="Ages 5-8",
        )

    if st.button("Build Brand Profile", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before building a brand profile.")
            return
        try:
            update = progress_action("Building brand", 3)
            update(1, "Creating brand strategy")
            profile = build_brand_profile(target_niche, age_range)
            update(2, "Saving brand profile")
            output_path = save_brand_profile(profile)
            try:
                register_brand(profile)
                record_output_file(output_path)
            except Exception:
                pass
            update(3, "Brand ready")
            render_brand_profile(profile, output_path)
        except Exception as exc:
            st.error(f"Brand profile generation failed: {exc}")


def page_character_manager() -> None:
    st.header("Character Manager")
    st.write("Create a reusable mascot character that can stay consistent across a long book series.")

    left, right = st.columns(2)
    with left:
        target_niche = st.text_input("Target niche", placeholder="Desert science activity books")
        brand_name = st.text_input("Brand name", placeholder="Little Explorer Club")
    with right:
        audience = st.text_input("Audience", value="Children ages 5-8")

    if st.button("Generate Mascot Character", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before creating a character profile.")
            return
        try:
            update = progress_action("Creating character", 3)
            update(1, "Designing mascot identity")
            profile = build_character_profile(target_niche, brand_name, audience)
            update(2, "Saving character profile")
            output_path = save_character_profile(profile)
            try:
                register_character(profile)
                record_output_file(output_path)
            except Exception:
                pass
            update(3, "Character ready")
            render_character_profile(profile, output_path)
        except Exception as exc:
            st.error(f"Character generation failed: {exc}")


def page_style_library() -> None:
    st.header("Style Library")
    st.write("Save reusable illustration styles for covers, icons, characters, and coloring pages.")

    st.subheader("Saved Styles")
    try:
        styles = load_styles()
        for style in styles:
            render_style(style)
    except Exception as exc:
        st.error(f"Could not load styles: {exc}")

    st.divider()
    st.subheader("Create Custom Style")

    with st.form("custom_style_form"):
        style_name = st.text_input("Style name", placeholder="Cozy Nature Journal")
        image_prompt_modifiers = st.text_area(
            "Image prompt modifiers",
            placeholder="Warm natural colors, simple friendly characters, educational nature details...",
        )
        cover_modifiers = st.text_area(
            "Cover modifiers",
            placeholder="Clean cover scene with open space for title, friendly main subject...",
        )
        coloring_page_modifiers = st.text_area(
            "Coloring page modifiers",
            placeholder="Thick black outlines, no shading, large open spaces...",
        )
        icon_modifiers = st.text_area(
            "Icon modifiers",
            placeholder="Simple rounded icon, transparent background, clear silhouette...",
        )
        submitted = st.form_submit_button("Save Custom Style", type="primary")

    if submitted:
        try:
            style = IllustrationStyle(
                style_name=style_name,
                image_prompt_modifiers=image_prompt_modifiers,
                cover_modifiers=cover_modifiers,
                coloring_page_modifiers=coloring_page_modifiers,
                icon_modifiers=icon_modifiers,
            )
            output_path = save_style(style)
            st.success(f"Style saved to {output_path.as_posix()}")
            render_style(style)
        except Exception as exc:
            st.error(f"Could not save style: {exc}")


def page_translation_center() -> None:
    st.header("Translation Center")
    st.write("Create language packs for the current project.")

    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate or load a blueprint and content before translating.")
        return

    selected_languages = st.multiselect(
        "Languages",
        list(SUPPORTED_LANGUAGES),
        default=["French", "Spanish"],
    )

    if st.button("Generate Language Packs", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before translating projects.")
            return
        if not selected_languages:
            st.error("Choose at least one language.")
            return

        progress = st.progress(0, text="Starting translation")
        saved_paths: list[tuple[LanguagePack, Path]] = []

        for index, language in enumerate(selected_languages, start=1):
            try:
                progress.progress((index - 1) / len(selected_languages), text=f"Translating {language}")
                pack = translate_project(blueprint, units, language)  # type: ignore[arg-type]
                path = save_language_pack(pack)
                saved_paths.append((pack, path))
            except Exception as exc:
                st.error(f"{language} translation failed: {exc}")

        progress.progress(1.0, text="Translations complete")

        for pack, path in saved_paths:
            render_language_pack(pack, path)

    language_dir = current_project_dir() / "language_packs"
    if language_dir.exists():
        st.subheader("Saved Language Packs")
        for path in sorted(language_dir.glob("*.json")):
            try:
                pack = LanguagePack.model_validate_json(path.read_text(encoding="utf-8"))
                render_language_pack(pack, path)
            except Exception:
                st.warning(f"Could not read {path.name}")


def render_blueprint(blueprint: BookBlueprint) -> None:
    st.subheader(blueprint.title)
    st.caption(blueprint.subtitle)
    st.write(blueprint.promise)
    st.info(blueprint.unique_angle)

    cols = st.columns(2)
    cols[0].markdown("**Audience**")
    cols[0].write(blueprint.audience)
    cols[1].markdown("**KDP Positioning**")
    cols[1].write(blueprint.kdp_positioning)

    st.markdown("**Page Plan**")
    st.dataframe(
        [
            {"Page": page.page_number, "Type": page.page_type, "Title": page.title}
            for page in blueprint.page_plan
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_content_units(units: list[AnimalUnit]) -> None:
    for unit in units:
        with st.expander(unit.animal_name):
            st.write(unit.short_story)
            st.markdown("**Facts**")
            for fact in unit.fun_facts:
                st.write(f"- {fact}")
            st.markdown("**Vocabulary**")
            st.write(", ".join(unit.vocabulary_words))


def render_qc(items: list[QCItem], report_path: Path) -> None:
    st.success(f"Report saved to {report_path.as_posix()}")
    for item in items:
        text = f"{item.check}: {item.message}"
        if item.status == "pass":
            st.success(text)
        elif item.status == "warning":
            st.warning(text)
        else:
            st.error(text)


def render_dashboard_table(title: str, rows: list[object]) -> None:
    st.subheader(title)
    if not rows:
        st.caption("No items yet.")
        return
    st.dataframe([row.model_dump() for row in rows], use_container_width=True, hide_index=True)


def page_dashboard() -> None:
    st.header("Publishing Dashboard")
    st.write("Track your projects, brands, books, languages, and exports from one local homepage.")

    data: DashboardData = collect_dashboard_data()

    metric_columns = st.columns(4)
    for column, metric in zip(metric_columns, data.metrics, strict=False):
        column.metric(metric.label, metric.value)

    st.subheader("Publishing Activity")
    if data.chart_rows:
        st.bar_chart(data.chart_rows, x="category", y="count", use_container_width=True)
    else:
        st.caption("No activity to chart yet.")

    left, right = st.columns(2)
    with left:
        render_dashboard_table("Projects", data.project_rows)
        render_dashboard_table("Books", data.book_rows)
        render_dashboard_table("Languages", data.language_rows)
    with right:
        render_dashboard_table("Brands", data.brand_rows)
        render_dashboard_table("Exports", data.export_rows)


def _read_json_file(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def page_compliance_center() -> None:
    st.header("Compliance Center")
    st.write("Create an evidence package showing when and how this project was generated.")

    project_dir = current_project_dir()
    provenance_dir = project_dir / "provenance"
    prompt_history = _read_json_file(provenance_dir / "prompt_history.json", [])
    asset_registry = _read_json_file(provenance_dir / "asset_registry.json", [])
    file_hashes = _read_json_file(provenance_dir / "file_hashes.json", {})
    copyright_scan = _read_json_file(provenance_dir / "copyright_scan.json", {"warnings": []})
    trademark_scan = _read_json_file(provenance_dir / "trademark_scan.json", {"warnings": []})
    provenance = _read_json_file(provenance_dir / "project_provenance.json", {})

    copyright_warnings = copyright_scan.get("warnings", []) if isinstance(copyright_scan, dict) else []
    trademark_warnings = trademark_scan.get("warnings", []) if isinstance(trademark_scan, dict) else []

    cols = st.columns(4)
    cols[0].metric("Ownership Status", provenance.get("compliance_status", "pending") if isinstance(provenance, dict) else "pending")
    cols[1].metric("Assets", len(asset_registry) if isinstance(asset_registry, list) else 0)
    cols[2].metric("Prompts", len(prompt_history) if isinstance(prompt_history, list) else 0)
    cols[3].metric("File Hashes", len(file_hashes) if isinstance(file_hashes, dict) else 0)

    warning_cols = st.columns(2)
    warning_cols[0].metric("Copyright Warnings", len(copyright_warnings))
    warning_cols[1].metric("Trademark Warnings", len(trademark_warnings))

    if copyright_warnings:
        with st.expander("Copyright warnings", expanded=True):
            st.dataframe(copyright_warnings, use_container_width=True, hide_index=True)
    if trademark_warnings:
        with st.expander("Trademark warnings", expanded=True):
            st.dataframe(trademark_warnings, use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        if st.button("Generate Ownership Report", type="primary"):
            try:
                update = progress_action("Generating ownership report", 4)
                update(1, "Hashing project files")
                hash_project_files(project_dir)
                update(2, "Scanning copyright and trademark references")
                run_copyright_scan(project_dir)
                run_trademark_scan(project_dir)
                update(3, "Writing PDF report")
                report_path = generate_ownership_report(project_dir)
                update(4, "Ownership report ready")
                st.success(f"Ownership report ready: {report_path.as_posix()}")
            except Exception as exc:
                st.error(f"Ownership report failed: {exc}")
    with right:
        if st.button("Export Compliance Package"):
            try:
                update = progress_action("Exporting compliance package", 3)
                update(1, "Collecting provenance files")
                paths = export_compliance_package(project_dir)
                update(2, "Creating zip package")
                update(3, "Compliance package ready")
                st.success(f"Compliance folder ready: {paths['compliance_dir'].as_posix()}")
                if "zip_path" in paths:
                    st.info(f"Compliance ZIP ready: {paths['zip_path'].as_posix()}")
            except Exception as exc:
                st.error(f"Compliance export failed: {exc}")


def safe_name(text: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")


def generate_visual_assets(blueprint: BookBlueprint, units: list[AnimalUnit], placeholder: bool) -> list[Path]:
    assets_dir = current_project_dir() / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    selected_cover = load_selected_cover_concept()
    cover_prompt = selected_cover.image_prompt if selected_cover else f"{blueprint.title}. {blueprint.unique_angle}. {blueprint.visual_style}"
    paths = [
        generate_cover_image(
            cover_prompt,
            assets_dir / "cover.png",
            placeholder=placeholder,
        )
    ]
    for index, unit in enumerate(units, start=1):
        prefix = f"{index:02d}_{safe_name(unit.animal_name)}"
        paths.append(
            generate_character_image(
                f"{unit.animal_name}. {unit.habitat}. Friendly educational workbook character.",
                assets_dir / f"{prefix}_character.png",
                placeholder=placeholder,
            )
        )
        paths.append(
            generate_coloring_page(
                unit.coloring_page_prompt,
                assets_dir / f"{prefix}_coloring.png",
                placeholder=placeholder,
            )
        )
        paths.append(
            generate_icon(
                f"Simple kid-friendly icon for {unit.animal_name}",
                assets_dir / f"{prefix}_icon.png",
                placeholder=placeholder,
            )
        )
    return paths


def page_project_setup() -> None:
    st.header("Project Setup")
    existing = load_request()

    with st.form("project_setup_form"):
        left, right = st.columns(2)
        with left:
            theme = st.text_input("Book theme", value=existing.theme if existing else "Desert Animals Workbook")
            age_min = st.number_input("Minimum age", min_value=2, max_value=14, value=existing.age_min if existing else 5)
            age_max = st.number_input("Maximum age", min_value=2, max_value=14, value=existing.age_max if existing else 7)
            page_count = st.number_input("Page count", min_value=8, max_value=200, value=existing.page_count if existing else 48, step=2)
            trim_size = st.selectbox("Trim size", ["8.5 x 11 in", "8 x 10 in", "7 x 10 in", "6 x 9 in"])
        with right:
            color_mode = st.selectbox("Color mode", ["Black and white", "Full color", "Interior grayscale"])
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"])
            language = st.text_input("Language", value=existing.language if existing else "English")
            activity_types = st.multiselect(
                "Activity types",
                ["Coloring pages", "Mazes", "Word searches", "Dot-to-dot", "Tracing", "Matching", "Quiz", "Simple puzzles"],
                default=existing.activity_types if existing else ["Coloring pages", "Mazes", "Word searches", "Dot-to-dot"],
            )
            style_direction = st.text_area(
                "Style direction",
                value=existing.style_direction if existing else "Cute animal characters, clean bold outlines, friendly educational tone.",
            )
        submitted = st.form_submit_button("Save Project Setup", type="primary")

    if submitted:
        try:
            request = BookRequest(
                theme=theme,
                age_min=int(age_min),
                age_max=int(age_max),
                trim_size=trim_size,
                page_count=int(page_count),
                color_mode=color_mode,
                activity_types=activity_types,
                style_direction=style_direction,
                difficulty=difficulty,
                language=language,
            )
            path = save_request(request)
            st.success(f"Project setup saved to {path.as_posix()}")
        except Exception as exc:
            st.error(f"Please fix the setup: {exc}")


def page_generate_blueprint() -> None:
    st.header("Generate Blueprint")
    request = load_request()
    if request is None:
        st.warning("Save Project Setup first.")
        return

    st.json(json.loads(request.model_dump_json()))
    if st.button("Generate Book Blueprint", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating a blueprint.")
            return
        try:
            update = progress_action("Generating blueprint", 3)
            update(1, "Sending planning brief")
            blueprint = generate_book_blueprint(request)
            update(2, "Saving blueprint")
            path = save_blueprint(blueprint)
            update(3, "Blueprint ready")
            st.success(f"Blueprint saved to {path.as_posix()}")
            render_blueprint(blueprint)
        except Exception as exc:
            st.error(f"Blueprint generation failed: {exc}")

    blueprint = load_blueprint()
    if blueprint:
        render_blueprint(blueprint)


def page_generate_content() -> None:
    st.header("Generate Content")
    blueprint = load_blueprint()
    if blueprint is None:
        st.warning("Generate or load a blueprint first.")
        return

    if st.button("Generate Book Content", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating content.")
            return
        try:
            update = progress_action("Generating content", 3)
            update(1, "Writing educational units")
            units = generate_content_units(blueprint)
            update(2, "Saving content")
            path = save_content_units(units)
            try:
                record_output_file(path)
            except Exception:
                pass
            st.session_state["current_content_units"] = ContentUnitBatch(units=units).model_dump_json()
            update(3, "Content ready")
            st.success(f"Content saved to {path.as_posix()}")
        except Exception as exc:
            st.error(f"Content generation failed: {exc}")

    units = load_content_units()
    if units:
        render_content_units(units)


def page_generate_activities() -> None:
    st.header("Generate Activities")
    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate blueprint and content first.")
        return

    if st.button("Generate Activity Data", type="primary"):
        try:
            update = progress_action("Generating activities", 3)
            update(1, "Building puzzles")
            activity_data, path = generate_and_save_activity_data(blueprint, units)
            update(2, "Saving activity data")
            update(3, "Activities ready")
            st.success(f"Activity data saved to {path.as_posix()}")
            st.json(activity_data)
        except Exception as exc:
            st.error(f"Activity generation failed: {exc}")

    existing = load_activity_data()
    if existing:
        st.json(existing)


def render_cover_concepts(concepts: CoverConceptSet) -> None:
    st.subheader("Ranked Cover Concepts")
    st.caption(concepts.positioning_summary)
    for concept in concepts.concepts:
        with st.expander(f"#{concept.rank}: {concept.concept_name}", expanded=concept.rank == 1):
            st.markdown("**Title placement**")
            st.write(concept.title_placement)
            st.markdown("**Focal character**")
            st.write(concept.focal_character)
            st.markdown("**Emotional hook**")
            st.write(concept.emotional_hook)
            st.markdown("**Color strategy**")
            st.write(concept.color_strategy)
            st.markdown("**Composition notes**")
            st.write(concept.composition_notes)
            st.markdown("**Image prompt**")
            st.code(concept.image_prompt)
            st.caption(f"Ranking reason: {concept.ranking_reason}")


def page_cover_lab() -> None:
    st.header("Cover Lab")
    st.write("Create and rank cover concepts before generating cover art.")

    request = load_request()
    blueprint = load_blueprint()
    default_niche = blueprint.title if blueprint else (request.theme if request else "Desert Animals Workbook")
    default_age = blueprint.audience if blueprint else (f"Ages {request.age_min}-{request.age_max}" if request else "Ages 5-7")
    default_style = blueprint.visual_style if blueprint else (request.style_direction if request else "Cute educational workbook style")

    with st.form("cover_lab_form"):
        niche = st.text_input("Niche", value=default_niche)
        age_range = st.text_input("Age range", value=default_age)
        style = st.text_area("Style", value=default_style)
        submitted = st.form_submit_button("Generate Cover Concepts", type="primary")

    if submitted:
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating cover concepts.")
            return
        try:
            update = progress_action("Generating cover concepts", 3)
            update(1, "Building cover strategy")
            concepts = generate_cover_concepts(niche, age_range, style)
            update(2, "Saving ranked concepts")
            path = save_cover_concepts(concepts)
            update(3, "Cover concepts ready")
            st.success(f"Cover concepts saved to {path.as_posix()}")
        except Exception as exc:
            st.error(f"Cover concept generation failed: {exc}")

    concepts = load_cover_concepts()
    if concepts is None:
        return

    render_cover_concepts(concepts)
    selected = st.selectbox(
        "Select concept for cover art",
        options=concepts.concepts,
        format_func=lambda concept: f"#{concept.rank}: {concept.concept_name}",
    )
    if st.button("Use Selected Cover Concept", type="primary"):
        path = save_selected_cover_concept(selected)
        st.success(f"Selected cover concept saved to {path.as_posix()}")

    current = load_selected_cover_concept()
    if current:
        st.info(f"Current selected concept: #{current.rank}: {current.concept_name}")


def page_generate_images() -> None:
    st.header("Generate Images")
    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate blueprint and content first.")
        return

    placeholder = st.checkbox("Use placeholder images", value=True)
    st.caption("Leave this on while testing. Turn it off only when you want real image API calls.")
    selected_cover = load_selected_cover_concept()
    if selected_cover:
        st.info(f"Cover art will use selected Cover Lab concept: #{selected_cover.rank}: {selected_cover.concept_name}")

    if st.button("Generate Visual Assets", type="primary"):
        if not placeholder and not get_settings().google_api_key:
            st.error("Add google_api_key or use placeholder images.")
            return
        try:
            update = progress_action("Generating images", 3)
            update(1, "Preparing prompts")
            paths = generate_visual_assets(blueprint, units, placeholder)
            update(2, "Saving PNG assets")
            update(3, "Images ready")
            st.success(f"Generated {len(paths)} PNG files")
            for path in paths:
                st.write(path.as_posix())
        except Exception as exc:
            st.error(f"Image generation failed: {exc}")


def page_build_pdf() -> None:
    st.header("Build PDF")
    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate blueprint and content first.")
        return

    if st.button("Build Interior PDF", type="primary"):
        try:
            update = progress_action("Building PDF", 3)
            update(1, "Laying out pages")
            output_pdf = current_project_dir() / "interior.pdf"
            pdf_path = build_interior_pdf(
                blueprint,
                units,
                load_activity_data(),
                current_project_dir() / "assets",
                output_pdf,
            )
            update(2, "Writing PDF")
            update(3, "PDF ready")
            st.success(f"Interior PDF exported to {pdf_path.as_posix()}")
        except Exception as exc:
            st.error(f"PDF build failed: {exc}")


def page_run_qc() -> None:
    st.header("Quality Control Report")
    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate blueprint and content first.")
        return

    if st.button("Run Quality Control", type="primary"):
        try:
            update = progress_action("Running QC", 3)
            update(1, "Checking files and content")
            items, report_path = run_quality_checks(
                blueprint,
                units,
                current_project_dir(),
                request=load_request(),
                activity_data=load_activity_data(),
            )
            update(2, "Writing report")
            update(3, "QC ready")
            render_qc(items, report_path)
        except Exception as exc:
            st.error(f"Quality control failed: {exc}")


def page_export_package() -> None:
    st.header("Export Package")
    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate blueprint and content first.")
        return

    st.write("This creates the KDP upload folder and a zip file with listing helper files.")
    if st.button("Export KDP Upload Package", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating KDP metadata.")
            return
        try:
            update = progress_action("Exporting package", 4)
            update(1, "Generating listing metadata")
            paths = export_kdp_upload_package(blueprint, units, current_project_dir())
            update(3, "Creating zip file")
            update(4, "Package ready")
            st.success(f"Zip ready: {paths['zip_path'].as_posix()}")
            st.write(f"Folder: {paths['package_dir'].as_posix()}")
        except Exception as exc:
            st.error(f"Package export failed: {exc}")


def page_etsy_export() -> None:
    st.header("Etsy Export")
    st.write("Create a printable Etsy bundle from the current workbook content.")

    blueprint = load_blueprint()
    units = load_content_units()
    if blueprint is None or not units:
        st.warning("Generate or load a blueprint and content before exporting an Etsy bundle.")
        return

    st.markdown("**Bundle includes**")
    st.write("- flashcards")
    st.write("- posters")
    st.write("- reward chart")
    st.write("- certificates")
    st.write("- worksheet pack")
    st.write("- printable coloring pages when image assets exist")

    if st.button("Export Etsy Bundle", type="primary"):
        try:
            update = progress_action("Exporting Etsy bundle", 4)
            update(1, "Creating printable PDFs")
            paths = export_etsy_bundle(blueprint, units, current_project_dir())
            try:
                record_output_file(paths["zip_path"])
            except Exception:
                pass
            update(3, "Creating ZIP package")
            update(4, "Etsy bundle ready")
            st.success(f"Etsy ZIP ready: {paths['zip_path'].as_posix()}")
            st.write(f"Folder: {paths['bundle_dir'].as_posix()}")
        except Exception as exc:
            st.error(f"Etsy export failed: {exc}")


def page_teacher_resources() -> None:
    st.header("Teacher Resources")
    st.write("Generate a K-5 classroom support pack from the current book blueprint.")

    blueprint = load_blueprint()
    if blueprint is None:
        st.warning("Generate or load a blueprint before creating teacher resources.")
        return

    if st.button("Export Teacher Pack", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating teacher resources.")
            return
        try:
            update = progress_action("Creating teacher pack", 4)
            update(1, "Generating lesson materials")
            paths = export_teacher_pack(blueprint, current_project_dir())
            try:
                record_output_file(paths["pdf_path"])
                record_output_file(paths["json_path"])
                record_output_file(paths["zip_path"])
            except Exception:
                pass
            update(3, "Writing PDF")
            update(4, "Teacher pack ready")
            st.success(f"Teacher pack PDF ready: {paths['pdf_path'].as_posix()}")
            st.info(f"Teacher pack ZIP ready: {paths['zip_path'].as_posix()}")
            st.write(f"Folder: {paths['pack_dir'].as_posix()}")
        except Exception as exc:
            st.error(f"Teacher pack export failed: {exc}")


def page_homeschool_center() -> None:
    st.header("Homeschool Center")
    st.write("Convert the current workbook blueprint into a parent-friendly homeschool product.")

    blueprint = load_blueprint()
    if blueprint is None:
        st.warning("Generate or load a blueprint before creating a homeschool pack.")
        return

    st.markdown("**Pack includes**")
    st.write("- weekly plans")
    st.write("- learning objectives")
    st.write("- daily activities")
    st.write("- parent guide")
    st.write("- progress tracker")

    if st.button("Export Homeschool Pack", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating homeschool resources.")
            return
        try:
            update = progress_action("Creating homeschool pack", 4)
            update(1, "Generating home-learning plan")
            paths = export_homeschool_pack(blueprint, current_project_dir())
            try:
                record_output_file(paths["pdf_path"])
                record_output_file(paths["json_path"])
                record_output_file(paths["zip_path"])
            except Exception:
                pass
            update(3, "Writing PDF")
            update(4, "Homeschool pack ready")
            st.success(f"Homeschool pack PDF ready: {paths['pdf_path'].as_posix()}")
            st.info(f"Homeschool pack ZIP ready: {paths['zip_path'].as_posix()}")
            st.write(f"Folder: {paths['pack_dir'].as_posix()}")
        except Exception as exc:
            st.error(f"Homeschool pack export failed: {exc}")


def render_marketing_preview(assets: MarketingAssets, paths: dict[str, Path]) -> None:
    st.success(f"Marketing assets saved: {paths['json_path'].as_posix()}")
    st.info(f"Summary file ready: {paths['summary_path'].as_posix()}")

    amazon = assets.amazon
    st.subheader("Amazon")
    st.write(f"**Title:** {amazon.title}")
    st.write(f"**Subtitle:** {amazon.subtitle}")
    st.write("**Backend keywords:**")
    st.write(", ".join(amazon.backend_keywords))

    cols = st.columns(4)
    cols[0].metric("Blog Articles", len(assets.blog_articles))
    cols[1].metric("Pinterest Ideas", len(assets.pinterest_pin_ideas))
    cols[2].metric("TikTok Scripts", len(assets.tiktok_scripts))
    cols[3].metric("YouTube Shorts", len(assets.youtube_shorts_scripts))

    with st.expander("A+ Content"):
        for item in assets.amazon.a_plus_content:
            st.write(f"- {item}")

    with st.expander("Email Launch Sequence"):
        for email in assets.email_launch_sequence:
            st.write(f"**{email.subject}**")
            st.caption(email.preview_text)


def page_marketing_center() -> None:
    st.header("Marketing Center")
    st.write("Generate complete launch assets from the current book blueprint and a saved brand profile.")

    blueprint = load_blueprint()
    if blueprint is None:
        st.warning("Generate or load a blueprint before creating marketing assets.")
        return

    brand_files = list_brand_profile_files()
    if not brand_files:
        st.warning("Create a brand in Brand Builder before generating marketing assets.")
        return

    selected_brand = st.selectbox(
        "Brand profile",
        options=brand_files,
        format_func=lambda path: path.stem,
    )
    brand = load_brand_profile(selected_brand)
    st.caption(f"Using brand: {brand.brand_name}")

    st.markdown("**Marketing pack includes**")
    st.write("- Amazon listing, backend keywords, and A+ content")
    st.write("- 5 SEO blog articles")
    st.write("- 20 Pinterest pin ideas")
    st.write("- 30 TikTok scripts")
    st.write("- 30 YouTube Shorts scripts")
    st.write("- 20 Facebook post ideas")
    st.write("- email launch sequence")

    if st.button("Generate Marketing Assets", type="primary"):
        if not get_settings().google_api_key:
            st.error("Add google_api_key in .env before generating marketing assets.")
            return
        try:
            update = progress_action("Generating marketing assets", 4)
            update(1, "Building campaign strategy")
            paths = export_marketing_assets(blueprint, brand)
            update(3, "Saving marketing files")
            assets = MarketingAssets.model_validate_json(paths["json_path"].read_text(encoding="utf-8"))
            update(4, "Marketing assets ready")
            render_marketing_preview(assets, paths)
        except Exception as exc:
            st.error(f"Marketing asset generation failed: {exc}")


def main() -> None:
    step = render_sidebar()
    st.title("KDP Activity Book Factory")
    st.caption("A guided local app for building KDP-ready children's activity workbook packages.")

    if step == "Dashboard":
        page_dashboard()
    elif step == "Research Center":
        page_research_center()
    elif step == "Brand Builder":
        page_brand_builder()
    elif step == "Character Manager":
        page_character_manager()
    elif step == "Style Library":
        page_style_library()
    elif step == "Translation Center":
        page_translation_center()
    elif step == "1. Project Setup":
        page_project_setup()
    elif step == "2. Generate Blueprint":
        page_generate_blueprint()
    elif step == "3. Generate Content":
        page_generate_content()
    elif step == "4. Generate Activities":
        page_generate_activities()
    elif step == "Cover Lab":
        page_cover_lab()
    elif step == "5. Generate Images":
        page_generate_images()
    elif step == "6. Build PDF":
        page_build_pdf()
    elif step == "7. Run QC":
        page_run_qc()
    elif step == "8. Export Package":
        page_export_package()
    elif step == "Etsy Export":
        page_etsy_export()
    elif step == "Teacher Resources":
        page_teacher_resources()
    elif step == "Homeschool Center":
        page_homeschool_center()
    elif step == "Marketing Center":
        page_marketing_center()
    elif step == "Compliance Center":
        page_compliance_center()


if __name__ == "__main__":
    main()

