# agent/tools/context_utils.py

import os
from agent.loader import load_pdf, load_html
from agent.customer_memory import load_customer_memory

def get_context_from_text_or_url(text, url, customer_id=None, pdf_path=None):
    context_parts = []

    if text and text.strip():
        context_parts.append(text.strip())

    if url and url.strip():
        try:
            html_context = load_html(url)
            context_parts.append(html_context)
        except Exception as e:
            context_parts.append(f"[Fehler beim Laden der URL: {e}]")

    if pdf_path and os.path.exists(pdf_path):
        try:
            pdf_context = load_pdf(pdf_path)
            context_parts.append(pdf_context)
        except Exception as e:
            context_parts.append(f"[Fehler beim Laden des PDFs: {e}]")

    if customer_id:
        memory = load_customer_memory(customer_id)
        if memory:
            context_parts.append(memory)

    return "\n\n".join([part for part in context_parts if part.strip()])
