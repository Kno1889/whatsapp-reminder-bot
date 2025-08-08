from PyPDF2 import PdfWriter, PdfReader

inputpdf = PdfReader(open("THE_CLEAR_QURAN_English_Translation_by_D.pdf", "rb"))

for i in range(len(inputpdf.pages)):
    output = PdfWriter()
    output.add_page(inputpdf.pages[i])
    with open(f"pages/{i}.pdf" , "wb") as outputStream:
        output.write(outputStream)
        