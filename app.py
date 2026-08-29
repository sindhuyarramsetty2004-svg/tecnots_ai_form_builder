import base64
import json
import os
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF
import streamlit as st
from groq import Groq


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="AI Form Builder",
    page_icon="🤖",
    layout="wide"
)


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

FIELD_TYPES = [
    "Single-line text",
    "Multi-line text",
    "Number",
    "Date",
    "Dropdown",
    "Checkbox"
]


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "fields" not in st.session_state:
    st.session_state.fields = []

if "saved_result" not in st.session_state:
    st.session_state.saved_result = None


# ---------------------------------------------------------
# FORM FIELD FUNCTIONS
# ---------------------------------------------------------

def add_field(label, field_type, required, options=""):
    st.session_state.fields.append({
        "id": len(st.session_state.fields) + 1,
        "label": label.strip(),
        "type": field_type,
        "required": required,
        "options": [
            x.strip()
            for x in options.split(",")
            if x.strip()
        ] if field_type == "Dropdown" else []
    })


def build_schema():
    return [
        {
            "label": field["label"],
            "type": field["type"],
            "required": field["required"],
            "options": field["options"]
        }
        for field in st.session_state.fields
    ]


# ---------------------------------------------------------
# PDF FUNCTIONS
# ---------------------------------------------------------

def extract_pdf_text(data):
    """
    Extract text from a normal text-based PDF.
    """
    doc = fitz.open(stream=data, filetype="pdf")

    text = "\n".join(
        page.get_text()
        for page in doc
    ).strip()

    page_count = len(doc)

    doc.close()

    return text, page_count


def image_to_data_url(data, mime):
    """
    Convert uploaded image bytes to base64 data URL.
    """

    encoded = base64.b64encode(data).decode()

    return f"data:{mime};base64,{encoded}"


# ---------------------------------------------------------
# GROQ AI EXTRACTION
# ---------------------------------------------------------

def ai_extract(schema, uploaded_bytes, file_type):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        st.error(
            "GROQ_API_KEY is not configured. "
            "Set the key in the terminal and restart the app."
        )
        return None

    client = Groq(api_key=api_key)

    system_prompt = """
You are a document information extraction assistant.

Your job is to extract information from a document
according to a user-defined form schema.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
  "results": [
    {
      "label": "Field Name",
      "value": "Extracted value",
      "found": true,
      "confidence": "High"
    }
  ]
}

Rules:

1. Return exactly one result for every field in the schema.
2. Use ONLY information actually present in the document.
3. Never guess.
4. Never invent information.
5. If a field is not present, use:
   value = ""
   found = false
   confidence = "Low"
6. Confidence must be exactly one of:
   High
   Medium
   Low
7. For Number fields, return only the numeric value.
8. For Checkbox fields, return true or false only when clearly supported.
9. For Dropdown fields, use exactly one of the provided options.
10. If a Dropdown value cannot be confidently matched, return an empty value.
11. Preserve names, emails, dates and other values accurately.
"""


    schema_text = json.dumps(
        schema,
        indent=2
    )


    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if file_type == "application/pdf":

        text, page_count = extract_pdf_text(
            uploaded_bytes
        )

        if not text:

            st.error(
                "This PDF does not contain readable text. "
                "Please upload a text-based PDF or JPG/PNG image."
            )

            return None

        user_prompt = f"""
Form schema:

{schema_text}

Document text:

{text[:100000]}

Extract the values that match the form schema.

Return JSON only.
"""


        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]


    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    else:

        if file_type == "image/png":
            mime = "image/png"

        else:
            mime = "image/jpeg"


        image_data_url = image_to_data_url(
            uploaded_bytes,
            mime
        )


        user_prompt = f"""
Form schema:

{schema_text}

Read the uploaded document image carefully.

Extract only information that is actually visible
in the document.

Return JSON only.
"""


        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]


    # -----------------------------------------------------
    # CALL GROQ
    # -----------------------------------------------------

    try:

        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            temperature=0,
            max_completion_tokens=2000,
            response_format={
                "type": "json_object"
            }
        )


        raw = response.choices[0].message.content

        if not raw:
            st.error("Groq returned an empty response.")
            return None


        raw = raw.strip()


        # Remove markdown fences if model adds them
        if raw.startswith("```json"):
            raw = raw[7:]

        elif raw.startswith("```"):
            raw = raw[3:]


        if raw.endswith("```"):
            raw = raw[:-3]


        raw = raw.strip()


        parsed = json.loads(raw)


        # Expected format:
        #
        # {
        #   "results": [...]
        # }

        if isinstance(parsed, dict):

            results = parsed.get("results")

            if isinstance(results, list):
                return results


        # Fallback if model returns an array
        if isinstance(parsed, list):
            return parsed


        st.error(
            "Groq returned an unexpected JSON format."
        )

        return None


    except Exception as e:

        st.error(
            f"Groq AI extraction failed: {e}"
        )

        return None


# ---------------------------------------------------------
# RENDER INPUT
# ---------------------------------------------------------

def render_input(
    field,
    value,
    key,
    missing=False
):

    label = field["label"]

    if missing:
        label += " ⚠️"


    field_type = field["type"]


    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    if field_type == "Single-line text":

        return st.text_input(
            label,
            value=str(value or ""),
            key=key
        )


    # -----------------------------------------------------
    # MULTI LINE
    # -----------------------------------------------------

    if field_type == "Multi-line text":

        return st.text_area(
            label,
            value=str(value or ""),
            key=key
        )


    # -----------------------------------------------------
    # NUMBER
    # -----------------------------------------------------

    if field_type == "Number":

        try:

            number_value = (
                float(value)
                if value not in ("", None)
                else 0.0
            )

        except Exception:

            number_value = 0.0


        return st.number_input(
            label,
            value=number_value,
            key=key
        )


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    if field_type == "Date":

        if value:

            try:
                selected_date = date.fromisoformat(
                    str(value)[:10]
                )

            except Exception:
                selected_date = date.today()

        else:
            selected_date = date.today()


        return st.date_input(
            label,
            value=selected_date,
            key=key
        )


    # -----------------------------------------------------
    # DROPDOWN
    # -----------------------------------------------------

    if field_type == "Dropdown":

        options = field.get(
            "options",
            []
        )

        choices = [""] + options

        current_value = (
            value
            if value in options
            else ""
        )

        index = choices.index(
            current_value
        )


        return st.selectbox(
            label,
            choices,
            index=index,
            key=key
        )


    # -----------------------------------------------------
    # CHECKBOX
    # -----------------------------------------------------

    if field_type == "Checkbox":

        checked = (
            str(value).lower() == "true"
            if value is not None
            else False
        )

        return st.checkbox(
            label,
            value=checked,
            key=key
        )


# ---------------------------------------------------------
# RESET EXTRACTION
# ---------------------------------------------------------

def reset_extraction():

    keys_to_delete = [
        key
        for key in st.session_state.keys()
        if key.startswith("result_")
    ]


    for key in keys_to_delete:
        del st.session_state[key]


    st.session_state.saved_result = None


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

st.title(
    "🤖 AI-Powered Form Builder & Document Autofill"
)

st.caption(
    "Build any form → upload a PDF/image → "
    "extract values using the form schema → "
    "review → save."
)


# ---------------------------------------------------------
# TWO COLUMN LAYOUT
# ---------------------------------------------------------

left, right = st.columns(
    [1, 1.25]
)


# =========================================================
# LEFT: DYNAMIC FORM BUILDER
# =========================================================

with left:

    st.subheader(
        "1. Dynamic Form Builder"
    )


    with st.form(
        "add_field",
        clear_on_submit=True
    ):

        label = st.text_input(
            "Field label",
            placeholder="e.g. Candidate Name"
        )


        field_type = st.selectbox(
            "Field type",
            FIELD_TYPES
        )


        required = st.checkbox(
            "Required"
        )


        options = st.text_input(
            "Dropdown options (comma-separated)",
            disabled=(
                field_type != "Dropdown"
            )
        )


        submit_field = st.form_submit_button(
            "➕ Add field",
            use_container_width=True
        )


        if submit_field:

            if not label.strip():

                st.warning(
                    "Please enter a field label."
                )

            else:

                add_field(
                    label,
                    field_type,
                    required,
                    options
                )

                st.rerun()


    # -----------------------------------------------------
    # SHOW FIELDS
    # -----------------------------------------------------

    if not st.session_state.fields:

        st.info(
            "No fields yet. Add fields above "
            "to start building your form."
        )


    else:

        for i, field in enumerate(
            st.session_state.fields
        ):

            c1, c2, c3 = st.columns(
                [3, 2, 1]
            )


            with c1:

                st.write(
                    f"**{i + 1}. {field['label']}**"
                )


            with c2:

                required_text = (
                    "Required"
                    if field["required"]
                    else "Optional"
                )

                st.caption(
                    f"{field['type']} • "
                    f"{required_text}"
                )


            with c3:

                if st.button(
                    "🗑️",
                    key=f"delete_{field['id']}"
                ):

                    st.session_state.fields.pop(i)

                    st.rerun()


        if st.button(
            "Clear all fields"
        ):

            st.session_state.fields = []

            reset_extraction()

            st.rerun()


# =========================================================
# RIGHT: LIVE FORM PREVIEW
# =========================================================

with right:

    st.subheader(
        "2. Live Form Preview"
    )


    if not st.session_state.fields:

        st.info(
            "Your live form preview will appear here."
        )


    else:

        for field in st.session_state.fields:

            field_type = field["type"]

            preview_key = (
                f"preview_{field['id']}"
            )


            if field_type == "Single-line text":

                st.text_input(
                    field["label"],
                    disabled=True,
                    key=preview_key
                )


            elif field_type == "Multi-line text":

                st.text_area(
                    field["label"],
                    disabled=True,
                    key=preview_key
                )


            elif field_type == "Number":

                st.number_input(
                    field["label"],
                    disabled=True,
                    key=preview_key
                )


            elif field_type == "Date":

                st.date_input(
                    field["label"],
                    disabled=True,
                    key=preview_key
                )


            elif field_type == "Dropdown":

                st.selectbox(
                    field["label"],
                    ["Select..."] + field["options"],
                    disabled=True,
                    key=preview_key
                )


            elif field_type == "Checkbox":

                st.checkbox(
                    field["label"],
                    disabled=True,
                    key=preview_key
                )


# =========================================================
# DOCUMENT UPLOAD
# =========================================================

st.divider()

st.subheader(
    "3. Document Upload & AI Extraction"
)


uploaded = st.file_uploader(
    "Upload a PDF, PNG, JPG or JPEG",
    type=[
        "pdf",
        "png",
        "jpg",
        "jpeg"
    ],
    help=(
        "Create at least one form field "
        "before extracting."
    )
)


if uploaded:

    allowed_extensions = {
        "pdf",
        "png",
        "jpg",
        "jpeg"
    }


    extension = (
        Path(uploaded.name)
        .suffix
        .lower()
        .lstrip(".")
    )


    # -----------------------------------------------------
    # INVALID FILE
    # -----------------------------------------------------

    if extension not in allowed_extensions:

        st.error(
            "Unsupported file type. "
            "Please upload PDF, JPG or PNG."
        )


    # -----------------------------------------------------
    # NO FIELDS
    # -----------------------------------------------------

    elif not st.session_state.fields:

        st.warning(
            "Please build the form first, "
            "then upload/extract the document."
        )


    # -----------------------------------------------------
    # VALID FILE
    # -----------------------------------------------------

    else:

        st.success(
            f"Uploaded successfully: {uploaded.name}"
        )


        # Show image preview
        if extension in {
            "png",
            "jpg",
            "jpeg"
        }:

            st.image(
                uploaded,
                caption="Uploaded document",
                width=500
            )


        # -------------------------------------------------
        # EXTRACT BUTTON
        # -------------------------------------------------

        if st.button(
            "✨ Extract & Autofill",
            type="primary",
            use_container_width=True
        ):

            reset_extraction()


            with st.spinner(
                "Reading document and extracting "
                "values using Groq AI..."
            ):

                file_type = (
                    "application/pdf"
                    if extension == "pdf"
                    else (
                        "image/jpeg"
                        if extension in {
                            "jpg",
                            "jpeg"
                        }
                        else "image/png"
                    )
                )


                results = ai_extract(
                    build_schema(),
                    uploaded.getvalue(),
                    file_type
                )


            # -------------------------------------------------
            # SAVE RESULTS
            # -------------------------------------------------

            if results is not None:

                for item in results:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue


                    label = item.get(
                        "label",
                        ""
                    )


                    if label:

                        st.session_state[
                            f"result_{label}"
                        ] = item


                st.success(
                    "Extraction completed. "
                    "Review and edit the fields below."
                )


# =========================================================
# REVIEW / EDIT / SAVE
# =========================================================

st.divider()

st.subheader(
    "4. Review, Edit & Save"
)


result_items = [
    st.session_state.get(
        f"result_{field['label']}"
    )
    for field in st.session_state.fields
]


has_results = any(
    item is not None
    for item in result_items
)


if not has_results:

    st.info(
        "After extraction, your pre-filled "
        "fields will appear here."
    )


else:

    edited = {}


    # -----------------------------------------------------
    # RENDER EXTRACTED FIELDS
    # -----------------------------------------------------

    for field in st.session_state.fields:

        item = st.session_state.get(
            f"result_{field['label']}",
            {}
        )


        value = (
            item.get("value", "")
            if item
            else ""
        )


        found = (
            item.get("found", False)
            if item
            else False
        )


        missing_required = (
            field["required"]
            and (
                not found
                or value in ("", None)
            )
        )


        if missing_required:

            st.warning(
                f"Required field "
                f"'{field['label']}' "
                f"was not confidently found. "
                f"Please complete it manually."
            )


        confidence = (
            item.get(
                "confidence",
                "Low"
            )
            if item
            else "Low"
        )


        st.caption(
            f"AI confidence: {confidence}"
        )


        edited[field["label"]] = render_input(
            field,
            value,
            f"edit_{field['id']}",
            missing_required
        )


    # -----------------------------------------------------
    # REQUIRED FIELD CHECK
    # -----------------------------------------------------

    required_missing = [
        field["label"]
        for field in st.session_state.fields
        if (
            field["required"]
            and edited.get(
                field["label"]
            ) in ("", None)
        )
    ]


    if required_missing:

        st.error(
            "Required fields still empty: "
            + ", ".join(required_missing)
        )


    # -----------------------------------------------------
    # SAVE BUTTON
    # -----------------------------------------------------

    if st.button(
        "💾 Save completed form",
        type="primary",
        use_container_width=True
    ):

        if required_missing:

            st.error(
                "Please complete all required "
                "fields before saving."
            )

        else:

            st.session_state.saved_result = edited

            st.success(
                "Form saved successfully."
            )


    # -----------------------------------------------------
    # DOWNLOAD JSON
    # -----------------------------------------------------

    if st.session_state.saved_result:

        json_data = json.dumps(
            st.session_state.saved_result,
            indent=2,
            default=str
        )


        st.download_button(
            "⬇️ Download saved form as JSON",
            data=json_data,
            file_name="completed_form.json",
            mime="application/json",
            use_container_width=True
        )


        with st.expander(
            "View saved JSON"
        ):

            st.json(
                st.session_state.saved_result
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Assessment-ready prototype • "
    "Schema-driven extraction • "
    "PDF/image support • "
    "Review/edit/save • "
    "Edge-case handling • Groq AI"
)