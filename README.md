# AI-Powered Dynamic Form Builder & Document Autofill

## About the Project

This project is a simple AI-powered form builder that can automatically fill form fields using information from an uploaded document.

The main idea behind this project is flexibility. Different users may need different fields, so instead of creating a fixed form, I created a dynamic form builder where users can add the fields they need.

For example, a user can create fields such as Candidate Name, Email, Phone Number, Skills, Date of Birth, etc. After creating the form, the user can upload a resume or another document. The application uses AI to find the relevant information and fill the form automatically.

The user can then check the extracted information, make changes if required, and save the final result as a JSON file.

## Main Features

- Create custom form fields
- Add or delete fields
- Set fields as Required or Optional
- Live form preview
- Support for different field types:
  - Single-line text
  - Multi-line text
  - Number
  - Date
  - Dropdown
  - Checkbox
- Upload PDF, PNG, JPG, and JPEG files
- Extract information from uploaded documents using AI
- Automatically fill the created form
- Show AI confidence levels
- Review and edit extracted information
- Manually enter missing information
- Validate required fields before saving
- Download the completed form as JSON

## Why I Used Dynamic Fields

I used dynamic fields because different users may have different requirements.

For example, one user may only need Name, Email, and Phone Number, while another user may need Name, Education, Skills, Experience, and Date of Birth.

Using dynamic fields makes the application more flexible instead of forcing every user to use the same fixed fields.

## How the Application Works

The application follows a simple workflow:

1. The user opens the application.
2. The user creates the required fields.
3. The user selects the field type and Required/Optional option.
4. The application shows a preview of the form.
5. The user uploads a PDF or image document.
6. The application processes the document.
7. The form schema and document information are given to the AI.
8. The AI extracts information related to the created fields.
9. The extracted information is automatically shown in the form.
10. The user reviews the information.
11. If anything is incorrect or missing, the user can edit it manually.
12. The user saves the completed form.
13. The final data can be downloaded as a JSON file.

## AI Extraction

The application uses the Groq API for AI-based information extraction.

The AI is instructed to use only the information available in the uploaded document.

It should not guess or create information that is not present in the document.

If the AI cannot confidently find a value, the field is left empty and the user can enter the information manually.

This helps avoid incorrect information being automatically saved.

## Confidence Levels

The application shows a confidence level for extracted information:

- High
- Medium
- Low

This gives the user an idea of how confident the AI is about the extracted value.

If the confidence is low, the user can review that field carefully and make changes if necessary.

## Review and Edit

The extracted information is not directly treated as final data.

The user gets an opportunity to review the values before saving.

If the AI extracts an incorrect value, the user can manually correct it.

If a required field is missing, the application asks the user to complete it before saving.

## Supported Documents

The application supports:

- PDF
- PNG
- JPG
- JPEG

For PDF files, PyMuPDF is used to extract readable text.

For image files, the image is provided to the AI for document understanding and extraction.

## Technologies Used

### Python

Python is used as the main programming language for the project.

### Streamlit

I used Streamlit to create the web application and user interface.

It made it easier to build the dynamic form, file upload, review, and save functionality using Python.

### Groq API

Groq API is used for AI-based document information extraction.

The extraction is based on the fields created by the user.

### PyMuPDF

PyMuPDF is used to read PDF files and extract text from them.

### Pillow

Pillow is used for handling image files such as PNG and JPEG.

### JSON

JSON is used to store and download the final completed form data in a structured format.

## Why JSON for the Final Output?

I used JSON because it is a simple and structured format for storing form data.

It is also easy to read, download, share, and use with other applications or APIs.

## Error and Edge Case Handling

I also added some basic handling for common situations.

### No Fields Created

If the user tries to extract information without creating any fields, the application asks the user to create the form first.

### Missing Information

If the information is not available in the document, the AI does not guess it. The field can be completed manually.

### Incorrect AI Result

If the AI extracts an incorrect value, the user can review and correct it before saving.

### Required Fields

If a required field is empty, the application does not allow the user to save the completed form until it is filled.

### Unsupported Files

The application accepts only PDF, PNG, JPG, and JPEG files.

### API Errors

If there is an API or extraction problem, the application displays an error message instead of stopping the entire application.

## Project Structure

```text
AI-Form-Builder/
│
├── app.py
├── requirements.txt
└── README.md
