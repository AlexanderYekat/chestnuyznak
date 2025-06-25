import os
import shutil

# Список папок для очистки
folders_to_clear = [
    os.path.join('.', 'inputs', 'goods'),
    os.path.join('.', 'inputs', 'set'),
    os.path.join('.', 'inputs', 'relations'),
    os.path.join('.', 'outputs'),
]

def clear_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Папка не найдена: {folder_path}")
        return
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Ошибка при удалении {file_path}: {e}")

if __name__ == '__main__':
    for folder in folders_to_clear:
        clear_folder(folder)
    print("Очистка входных и выходных данных завершена.")
