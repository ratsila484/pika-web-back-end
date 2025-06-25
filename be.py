from flask import Flask, send_file
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io


    

def remplir_pdf():
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica-Bold", 12)
    can.drawString(100, 450, "Dossier de nomination")
    can.drawString(300, 450, "3")
    can.drawString(400, 450, "Complet")
    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(open("templates/CF ANE.pdf", "rb"))
    output = PdfWriter()

    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    result = io.BytesIO()
    output.write(result)
    result.seek(0)

    return result  # ✅ tu retournes le PDF en mémoire, pas send_file directement
