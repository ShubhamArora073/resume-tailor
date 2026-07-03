import os
from pdf2docx import Converter as PdfConverter
from docx2pdf import convert


def pdf_to_docx(pdf_path: str, output_dir: str) -> str:
    """
    Convert a PDF file to DOCX format.

    Args:
        pdf_path: Path to the input PDF file
        output_dir: Directory where the output DOCX will be created

    Returns:
        Path to the created DOCX file

    Raises:
        FileNotFoundError: If pdf_path does not exist
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    docx_path = os.path.join(output_dir, f"{filename}.docx")

    cv = PdfConverter(pdf_path)
    cv.convert(docx_path)
    cv.close()

    return docx_path


def docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """
    Convert a DOCX file to PDF format.

    Args:
        docx_path: Path to the input DOCX file
        output_dir: Directory where the output PDF will be created

    Returns:
        Path to the created PDF file

    Raises:
        FileNotFoundError: If docx_path does not exist
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX not found: {docx_path}")

    filename = os.path.splitext(os.path.basename(docx_path))[0]
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")

    convert(docx_path, pdf_path)

    return pdf_path
