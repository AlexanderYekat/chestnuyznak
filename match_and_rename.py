import os
import fitz
from PIL import Image
from pylibdmtx import pylibdmtx
import shutil
import re

def extract_gs1_data_matrix(image):
    decoded = pylibdmtx.decode(image)
    if decoded:
        return decoded[0].data.decode('utf-8')
    else:
        return None

def extract_first_two_marks_from_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    marks = []
    for page_num in range(min(2, len(pdf_document))):
        page = pdf_document[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        data = extract_gs1_data_matrix(img)
        if data:
            marks.append(data)
        else:
            marks.append(None)
    pdf_document.close()
    return marks

def extract_first_two_marks_from_csv(csv_path):
    marks = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 2:
                break
            marks.append(line.strip())
    return marks

def has_set_in_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    for page_num in range(min(2, len(pdf_document))):
        text = pdf_document[page_num].get_text()
        if re.search(r'набор', text, re.IGNORECASE):
            pdf_document.close()
            return True
    pdf_document.close()
    return False

def strip_after_1d(s):
    return s.split('\x1d')[0] if s else s

def safe_filename(s):
    # Заменяем все недопустимые символы на "_"
    return re.sub(r'[<>:"/\\|?*%+]', '_', s)

def main(folder_path):
    files = os.listdir(folder_path)
    pdf_files = [f for f in files if f.lower().endswith('.pdf')]
    csv_files = [f for f in files if f.lower().endswith('.csv')]
    print(f"Найдено PDF файлов: {len(pdf_files)}")
    print(f"Найдено CSV файлов: {len(csv_files)}")
    used_pdfs = set()
    used_csvs = set()
    pairs_found = 0

    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        pdf_marks = extract_first_two_marks_from_pdf(pdf_path)
        print(f"PDF: {pdf_file} -> марки: {pdf_marks}")
        if not all(pdf_marks):
            print(f"Не удалось извлечь обе марки из PDF: {pdf_file} (найдено: {pdf_marks})")
            continue  # если не удалось извлечь обе марки, пропускаем
        pdf_marks_stripped = [strip_after_1d(m) for m in pdf_marks]
        for csv_file in csv_files:
            if csv_file in used_csvs:
                continue
            csv_path = os.path.join(folder_path, csv_file)
            csv_marks = extract_first_two_marks_from_csv(csv_path)
            csv_marks_stripped = [strip_after_1d(m) for m in csv_marks]
            print(f"  Сравниваю с CSV: {csv_file} -> марки: {csv_marks}")
            print(f"    Сравниваю урезанные: PDF {pdf_marks_stripped} <-> CSV {csv_marks_stripped}")
            if pdf_marks_stripped == csv_marks_stripped:
                print(f"    Совпадение: {pdf_marks_stripped} == {csv_marks_stripped}")
                # Формируем новое имя
                base_name = f"{pdf_marks_stripped[0]}_{pdf_marks_stripped[1]}"
                if has_set_in_pdf(pdf_path):
                    base_name += "_set"
                base_name = safe_filename(base_name)
                new_pdf = base_name + ".pdf"
                new_csv = base_name + ".csv"
                new_pdf_path = os.path.join(folder_path, new_pdf)
                new_csv_path = os.path.join(folder_path, new_csv)
                # Переименовываем только если новое имя отличается
                if os.path.abspath(pdf_path) != os.path.abspath(new_pdf_path):
                    shutil.move(pdf_path, new_pdf_path)
                    pdf_path = new_pdf_path  # обновляем путь для csv проверки
                if os.path.abspath(csv_path) != os.path.abspath(new_csv_path):
                    shutil.move(csv_path, new_csv_path)
                used_pdfs.add(pdf_file)
                used_csvs.add(csv_file)
                pairs_found += 1
                break  # pdf уже обработан
            else:
                print(f"    Не совпало: {pdf_marks_stripped} != {csv_marks_stripped}")
    if pairs_found == 0:
        print("Не найдено ни одной пары PDF/CSV с совпадающими марками.")
    else:
        print(f"Всего совпадений: {pairs_found}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Использование: python match_and_rename.py <папка>")
    else:
        main(sys.argv[1]) 