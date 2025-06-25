import os
import csv
import json
import fitz  # PyMuPDF
import re
import sys
from datetime import datetime

def extract_gtin_from_filename(filename):
    """
    Извлекает GTIN из имени файла.
    Ожидаемый формат: ...gtin_XXXXXXXXXXXXXX...
    """
    match = re.search(r'gtin_(\d{14})', filename)
    if match:
        return match.group(1)
    return None

def load_identifiers_from_csv(csv_filepath):
    """
    Читает CSV-файл как обычный текстовый файл и возвращает список идентификаторов (каждая строка).
    """
    identifiers = []
    print(f"DEBUG: Загрузка идентификаторов из: {csv_filepath}")
    with open(csv_filepath, 'r', encoding='utf-8') as f:
        for row_num, line in enumerate(f):
            raw_identifier = line.strip()
            # Удаляем BOM, если он есть, и обрезаем пробелы
            cleaned_identifier = raw_identifier.lstrip('\ufeff')
            if cleaned_identifier: # Добавляем только непустые строки
                identifiers.append(cleaned_identifier)
                print(f"DEBUG: Файл: {csv_filepath}, Строка: {row_num + 1}, Сырой идентификатор: '{raw_identifier}', Очищенный идентификатор: '{cleaned_identifier}'")
            else:
                print(f"DEBUG: Файл: {csv_filepath}, Строка: {row_num + 1}: Пустая строка.")
    print(f"DEBUG: Загружено {len(identifiers)} идентификаторов из {csv_filepath}")
    return identifiers

def get_pdf_page(pdf_filepath, page_number):
    """
    Извлекает конкретную страницу из PDF-файла в виде нового PDF-документа.
    Возвращает объект fitz.Document, содержащий только запрошенную страницу.
    """
    doc = fitz.open(pdf_filepath)
    if 0 <= page_number < doc.page_count:
        new_doc = fitz.open()  # Создаем новый пустой PDF
        new_doc.insert_pdf(doc, from_page=page_number, to_page=page_number) # Вставляем одну страницу
        doc.close()
        return new_doc
    doc.close()
    return None

def parse_relations(relations_dir):
    """
    Разбирает все JSON-файлы в каталоге связей и возвращает словарь,
    сопоставляющий unitSerialNumber с его списком sntins.
    """
    relations_map = {}
    for filename in os.listdir(relations_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(relations_dir, filename)
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                if 'aggregationUnits' in data:
                    for unit in data['aggregationUnits']:
                        unit_serial = unit.get('unitSerialNumber')
                        sntins = unit.get('sntins', [])
                        if unit_serial and sntins:
                            relations_map[unit_serial] = sntins
    return relations_map

def main():
    # Определяем входные/выходные каталоги
    goods_dir = os.path.join('.', 'inputs', 'goods')
    set_dir = os.path.join('.', 'inputs', 'set')
    relations_dir = os.path.join('.', 'inputs', 'relations')
    output_dir = os.path.join('.', 'outputs')

    # Создаем выходной каталог, если его нет
    os.makedirs(output_dir, exist_ok=True)

    # Настраиваем логирование в файл
    log_filename = os.path.join(output_dir, f'log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log')
    original_stdout = sys.stdout
    try:
        sys.stdout = open(log_filename, 'w', encoding='utf-8')
        print(f"Логирование начато в файл: {log_filename}")

        # Счетчик предупреждений
        warnings_count = 0

        # Шаг 1: Загружаем все идентификаторы и информацию о страницах PDF
        # Добавляем gtin для товаров
        all_identifiers_map = {} # {'идентификатор': {'pdf_path': '...', 'page_number': N, 'gtin': '...'}}

        # Обрабатываем каталог товаров
        goods_files = os.listdir(goods_dir)
        csv_files = [f for f in goods_files if f.endswith('.csv')]
        pdf_files = [f for f in goods_files if f.endswith('.pdf')]
        if len(csv_files) == 1 and len(pdf_files) == 1 and len(goods_files) == 2:
            # Особый случай: в папке только один csv и один pdf
            csv_filepath = os.path.join(goods_dir, csv_files[0])
            pdf_filepath = os.path.join(goods_dir, pdf_files[0])
            gtin_from_file = extract_gtin_from_filename(os.path.splitext(csv_files[0])[0])
            if os.path.exists(pdf_filepath):
                identifiers = load_identifiers_from_csv(csv_filepath)
                for i, identifier in enumerate(identifiers):
                    if gtin_from_file:
                        all_identifiers_map[identifier] = {'pdf_path': pdf_filepath, 'page_number': i, 'gtin': gtin_from_file}
                    else:
                        sys.__stdout__.write(f"Предупреждение: Не удалось извлечь GTIN из имени файла {csv_files[0]}. Идентификатор {identifier} не будет связан с GTIN.\n")
                        warnings_count += 1
                        print(f"Предупреждение: Не удалось извлечь GTIN из имени файла {csv_files[0]}. Идентификатор {identifier} не будет связан с GTIN.")
                        all_identifiers_map[identifier] = {'pdf_path': pdf_filepath, 'page_number': i, 'gtin': None}
            else:
                sys.__stdout__.write(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}\n")
                warnings_count += 1
                print(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}")
        else:
            # Обычный режим: перебираем все csv
            for filename in goods_files:
                if filename.endswith('.csv'):
                    base_name = filename[:-4] # Удаляем .csv
                    csv_filepath = os.path.join(goods_dir, filename)
                    pdf_filepath = os.path.join(goods_dir, base_name + '.pdf')
                    # Extract GTIN from the filename for goods
                    gtin_from_file = extract_gtin_from_filename(base_name)

                    if os.path.exists(pdf_filepath):
                        identifiers = load_identifiers_from_csv(csv_filepath)
                        for i, identifier in enumerate(identifiers):
                            if gtin_from_file:
                                all_identifiers_map[identifier] = {'pdf_path': pdf_filepath, 'page_number': i, 'gtin': gtin_from_file}
                            else:
                                sys.__stdout__.write(f"Предупреждение: Не удалось извлечь GTIN из имени файла {filename}. Идентификатор {identifier} не будет связан с GTIN.\n")
                                warnings_count += 1
                                print(f"Предупреждение: Не удалось извлечь GTIN из имени файла {filename}. Идентификатор {identifier} не будет связан с GTIN.")
                                all_identifiers_map[identifier] = {'pdf_path': pdf_filepath, 'page_number': i, 'gtin': None} # Store None if GTIN extraction fails
                    else:
                        sys.__stdout__.write(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}\n")
                        warnings_count += 1
                        print(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}")

        # Обрабатываем каталог наборов (аналогично товарам, но GTIN для самих наборов не важен)
        for filename in os.listdir(set_dir):
            if filename.endswith('.csv'):
                base_name = filename[:-4] # Удаляем .csv
                csv_filepath = os.path.join(set_dir, filename)
                pdf_filepath = os.path.join(set_dir, base_name + '.pdf')

                if os.path.exists(pdf_filepath):
                    identifiers = load_identifiers_from_csv(csv_filepath)
                    for i, identifier in enumerate(identifiers):
                        all_identifiers_map[identifier] = {'pdf_path': pdf_filepath, 'page_number': i, 'gtin': None} # GTIN for set itself is None/not relevant
                else:
                    sys.__stdout__.write(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}\n")
                    warnings_count += 1
                    print(f"Предупреждение: Не найден соответствующий PDF-файл для {csv_filepath}")

        print("DEBUG: Загруженная карта идентификаторов (all_identifiers_map):")
        for identifier, details in all_identifiers_map.items():
            print(f"DEBUG:   '{identifier}': {details}")
        print("DEBUG: Конец загруженной карты идентификаторов.")

        # Шаг 2: Разбираем JSON-файлы связей
        relations_map = parse_relations(relations_dir)
        print("DEBUG: Загруженная карта связей (relations_map):")
        for unit_serial, sntins_list in relations_map.items():
            print(f"DEBUG:   Набор: '{unit_serial}', Товары: {sntins_list}")
        print("DEBUG: Конец загруженной карты связей.")

        # Шаг 3: Генерируем объединенные PDF-файлы, сгруппированные по GTIN
        # Словарь для хранения PDF-документов для каждого GTIN
        # {'gtin': fitz.Document object}
        output_pdfs_by_gtin = {}

        for unit_serial, sntins_list in relations_map.items():
            print(f"DEBUG: Обработка набора: '{unit_serial}'")
            if unit_serial in all_identifiers_map:
                set_info = all_identifiers_map[unit_serial]
                set_pdf_path = set_info['pdf_path']
                set_page_num = set_info['page_number']

                current_bundle_gtin = None
                # Определяем GTIN для этого *пакета* набора и товаров.
                # Берем GTIN первого товара в списке sntins_list
                if sntins_list:
                    first_sntin = sntins_list[0]
                    if first_sntin in all_identifiers_map and all_identifiers_map[first_sntin]['gtin']:
                        current_bundle_gtin = all_identifiers_map[first_sntin]['gtin']
                    else:
                        sys.__stdout__.write(f"Предупреждение: Не удалось найти GTIN для первого товара {first_sntin} в наборе {unit_serial}. Пропускаем этот набор.\n")
                        warnings_count += 1
                        print(f"Предупреждение: Не удалось найти GTIN для первого товара {first_sntin} в наборе {unit_serial}. Пропускаем этот набор.")
                        continue

                if current_bundle_gtin:
                    if current_bundle_gtin not in output_pdfs_by_gtin:
                        output_pdfs_by_gtin[current_bundle_gtin] = fitz.open()

                    # Добавляем страницу набора
                    temp_set_doc = get_pdf_page(set_pdf_path, set_page_num)
                    if temp_set_doc:
                        output_pdfs_by_gtin[current_bundle_gtin].insert_pdf(temp_set_doc)
                        temp_set_doc.close()
                    else:
                        sys.__stdout__.write(f"Предупреждение: Не удалось получить страницу PDF для набора: {unit_serial}\n")
                        warnings_count += 1
                        print(f"Предупреждение: Не удалось получить страницу PDF для набора: {unit_serial}")
                        continue # Пропускаем этот пакет, если страница набора не может быть получена

                    # Добавляем страницы товаров для этого пакета
                    for sntin in sntins_list:
                        print(f"DEBUG:   Поиск товара: '{sntin}'")
                        if sntin in all_identifiers_map:
                            good_info = all_identifiers_map[sntin]
                            gtin_of_good = good_info['gtin'] # Получаем GTIN из all_identifiers_map
                            
                            if gtin_of_good == current_bundle_gtin: # Убеждаемся, что соответствует GTIN пакета
                                temp_good_doc = get_pdf_page(good_info['pdf_path'], good_info['page_number'])
                                if temp_good_doc:
                                    output_pdfs_by_gtin[current_bundle_gtin].insert_pdf(temp_good_doc)
                                    temp_good_doc.close()
                                else:
                                    sys.__stdout__.write(f"Предупреждение: Не удалось получить страницу PDF для товара: {sntin}\n")
                                    warnings_count += 1
                                    print(f"Предупреждение: Не удалось получить страницу PDF для товара: {sntin}")
                            else:
                                sys.__stdout__.write(f"Предупреждение: GTIN товара {sntin} ({gtin_of_good}) не соответствует GTIN набора ({current_bundle_gtin}). Пропускаем этот товар.\n")
                                warnings_count += 1
                                print(f"Предупреждение: GTIN товара {sntin} ({gtin_of_good}) не соответствует GTIN набора ({current_bundle_gtin}). Пропускаем этот товар.")
                        else:
                            sys.__stdout__.write(f"Предупреждение: Идентификатор товара {sntin} не найден в CSV-файлах.\n")
                            warnings_count += 1
                            print(f"Предупреждение: Идентификатор товара {sntin} не найден в CSV-файлах.")
                else:
                    sys.__stdout__.write(f"Предупреждение: Не удалось определить GTIN для набора {unit_serial}. Пропускаем.\n")
                    warnings_count += 1
                    print(f"Предупреждение: Не удалось определить GTIN для набора {unit_serial}. Пропускаем.")
            else:
                sys.__stdout__.write(f"Предупреждение: Идентификатор набора {unit_serial} не найден в CSV-файлах. Пропускаем.\n")
                warnings_count += 1
                print(f"Предупреждение: Идентификатор набора {unit_serial} не найден в CSV-файлах. Пропускаем.")

        # Сохраняем все сгенерированные PDF-файлы
        for gtin, pdf_doc in output_pdfs_by_gtin.items():
            output_filename = os.path.join(output_dir, f'combined_gtin_{gtin}.pdf')
            pdf_doc.save(output_filename)
            pdf_doc.close()
            print(f"Создан файл: {output_filename}")

        print("Программа завершила работу.")

        if warnings_count == 0:
            sys.__stdout__.write("Предупреждений не было.\n")
            print("Предупреждений не было.")

    finally:
        sys.stdout.close()
        sys.stdout = original_stdout # Восстанавливаем стандартный вывод
        print(f"Логирование завершено. Подробности см. в файле: {log_filename}")

if __name__ == '__main__':
    main() 