import os
import sys
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
    from datetime import datetime
    output_dir = os.path.join('.', 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    log_filename = os.path.join(output_dir, f'log_match_and_rename_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log')
    original_stdout = sys.stdout
    pairs_found = 0
    pair_number = 1

    try:
        sys.stdout = open(log_filename, 'w', encoding='utf-8')
        files = os.listdir(folder_path)
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        csv_files = [f for f in files if f.lower().endswith('.csv')]
        print(f"Найдено PDF файлов: {len(pdf_files)}")
        print(f"Найдено CSV файлов: {len(csv_files)}")
        used_pdfs = set()
        used_csvs = set()

        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            pdf_marks = extract_first_two_marks_from_pdf(pdf_path)
            print(f"PDF: {pdf_file} -> марки: {pdf_marks}")
            if not all(pdf_marks):
                print(f"Не удалось извлечь обе марки из PDF: {pdf_file} (найдено: {pdf_marks})")
                continue  # если не удалось извлечь обе марки, пропускаем
            pdf_marks_stripped = [strip_after_1d(m) for m in pdf_marks]
            found_pair = False
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
                    # Определяем основу имени (до расширения)
                    pdf_base = os.path.splitext(pdf_file)[0]
                    csv_base = os.path.splitext(csv_file)[0]
                    # Берём общую часть основы, если она совпадает, иначе используем pdf_base
                    if pdf_base == csv_base:
                        base_name = pdf_base
                    else:
                        base_name = pdf_base  # или можно реализовать более сложную логику объединения
                    base_name = safe_filename(base_name)
                    # Добавляем _set, если найдено слово 'набор' в PDF
                    set_suffix = "_set" if has_set_in_pdf(pdf_path) else ""
                    new_pdf = f"{base_name}_{pair_number}{set_suffix}.pdf"
                    new_csv = f"{base_name}_{pair_number}{set_suffix}.csv"
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
                    pair_number += 1
                    found_pair = True
                    break  # pdf уже обработан
                else:
                    print(f"    Не совпало: {pdf_marks_stripped} != {csv_marks_stripped}")
            # Если не найдено ни одной пары для этого PDF, выводим в консоль
            if not found_pair:
                sys.stdout.close()
                sys.stdout = original_stdout
                print(f"Для PDF {pdf_file} не найдено ни одной подходящей пары CSV.")
                sys.stdout = open(log_filename, 'a', encoding='utf-8')
        if pairs_found != 0:
            print(f"Всего совпадений: {pairs_found}")
    finally:
        if sys.stdout != original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
    # После завершения логирования — выводим в консоль, если не найдено ни одной пары
    if pairs_found == 0:
        print("Не найдено ни одной пары PDF/CSV с совпадающими марками.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python match_and_rename.py <папка>")
    else:
        main(sys.argv[1]) 