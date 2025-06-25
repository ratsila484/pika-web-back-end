from flask import Flask, send_file
from be import remplir_pdf

app = Flask(__name__)     

@app.route("/remplir-pdf") 
def route_remplir_pdf():  # ✅ nom différent
    result = remplir_pdf()  # on appelle la vraie fonction
    return send_file(result, download_name="pdf_rempli.pdf", as_attachment=True)

app.run(host="0.0.0.0", port=5000, debug=True)