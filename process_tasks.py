import os
import sys
import shutil
import subprocess
import datetime
import zipfile

# Получить текущую дату в формате YYYYMMDD
current_date = datetime.datetime.now().strftime('%Y%m%d')
tasks_root = os.path.abspath(os.path.join('..', 'tasks', current_date))

if not os.path.exists(tasks_root):
    print(f'Папка с задачами не найдена: {tasks_root}')
    sys.exit(1)

# Получить список подпапок
subfolders = [os.path.join(tasks_root, d) for d in os.listdir(tasks_root) if os.path.isdir(os.path.join(tasks_root, d))]

for subfolder in subfolders:
    print(f'\n=== Обработка папки: {subfolder} ===')
    # 0. Очистить входные/выходные папки перед каждой задачей
    subprocess.run([sys.executable, 'clear.py'], check=True)
    
    # --- ДОБАВЛЕНО: Распаковка zip, если нет pdf/csv, но есть zip ---
    files_in_subfolder = os.listdir(subfolder)
    has_pdf_or_csv = any(f.lower().endswith(('.pdf', '.csv')) for f in files_in_subfolder)
    zip_files = [f for f in files_in_subfolder if f.lower().endswith('.zip')]
    if not has_pdf_or_csv and zip_files:
        zip_path = os.path.join(subfolder, zip_files[0])  # Берём первый найденный zip
        print(f'Распаковываю архив: {zip_path}')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(subfolder)
        # Обновляем список файлов после распаковки
        files_in_subfolder = os.listdir(subfolder)
    # --- КОНЕЦ ДОБАВЛЕНИЯ ---

    # 1. Запустить match_and_rename.py
    subprocess.run([sys.executable, 'match_and_rename.py', subfolder], check=True)

    # 2. Копировать файлы в inputs
    # (Очистка папок теперь выполняется через clear.py, здесь только копирование)

    # Копировать .json в inputs/relations
    for f in os.listdir(subfolder):
        if f.lower().endswith('.json'):
            shutil.copy2(os.path.join(subfolder, f), os.path.join('inputs', 'relations', f))

    # Копировать наборы и товары
    for f in os.listdir(subfolder):
        if f.lower().endswith('.pdf') or f.lower().endswith('.csv'):
            src = os.path.join(subfolder, f)
            # Проверяем по суффиксу _set
            if f.lower().endswith('_set.pdf') or f.lower().endswith('_set.csv'):
                shutil.copy2(src, os.path.join('inputs', 'set', f))
            else:
                shutil.copy2(src, os.path.join('inputs', 'goods', f))

    # 3. Запустить main.py
    subprocess.run([sys.executable, 'main.py'], check=True)

    # 4. Копировать результаты из outputs/ в output подпапки задачи
    output_src = os.path.join('.', 'outputs')
    output_dst = os.path.join(subfolder, 'output')
    os.makedirs(output_dst, exist_ok=True)
    for f in os.listdir(output_src):
        shutil.copy2(os.path.join(output_src, f), os.path.join(output_dst, f))

print('\n=== Обработка всех задач завершена! ===') 