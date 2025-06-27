import fitz
import csv
from pyzbar.pyzbar import decode
from PIL import Image
import io
import os
import logging
from pylibdmtx import pylibdmtx

def extract_gs1_data_matrix(image):
    decoded = pylibdmtx.decode(image)
    if decoded:
        return decoded[0].data.decode('utf-8')
    else:
        return None


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_datamatrix_from_pdf(pdf_path, csv_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    data_list = []

    # Iterate through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        logger.info(f"Processing page {page_num + 1}")
        
        # Get the page as an image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save the image for debugging
        data = extract_gs1_data_matrix(img)
        if data:
            data_list.append({'data': data})
        else:
            print("Data Matrix коды не найдены в изображениях.")
            return

    # Close the PDF
    pdf_document.close()

    # Write the extracted codes to CSV
    if data_list:
        with open(csv_path, 'w', encoding='utf-8') as txtfile:
            for item in data_list:
                print("data=",item['data'])
                txtfile.write(f"{item['data']}\n")
    else:
        print("Data Matrix коды не найдены в изображениях.")

def find_pdf_files(root_dir):
    pdf_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return pdf_files
# Usage

root_directory = '.'

pdf_files = find_pdf_files(root_directory)

for pdf_file in pdf_files:
    # Создаем имя выходного файла, заменяя расширение .pdf на .txt
    print("pdf_file=",pdf_file)
    output_file = os.path.splitext(pdf_file)[0] + '.csv'
    print("output_file=",output_file)
    extract_datamatrix_from_pdf(pdf_file, output_file)