import csv
from prettytable import PrettyTable

def read_and_summarize_nft_stats(file_path):
    # Статистика для подсчета
    total_stats = {
        "uncommon": 0,
        "rare": 0,
        "legendary": 0,
        "mythical": 0
    }

    # Создаем таблицу
    table = PrettyTable()
    table.field_names = ["Address", "Uncommon", "Rare", "Legendary", "Mythical"]

    # Чтение данных из файла
    with open(file_path, mode='r', newline='') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            # Добавляем строки в таблицу
            table.add_row([row["address"], row["uncommon"], row["rare"], row["legendary"], row["mythical"]])
            # Суммируем статистику
            total_stats["uncommon"] += int(row["uncommon"])
            total_stats["rare"] += int(row["rare"])
            total_stats["legendary"] += int(row["legendary"])
            total_stats["mythical"] += int(row["mythical"])

    # Выводим таблицу
    print(table)

    # Выводим общую статистику
    total_table = PrettyTable()
    total_table.field_names = ["Type", "Total"]
    for type, total in total_stats.items():
        total_table.add_row([type.capitalize(), total])

    print("Общая статистика NFT:")
    print(total_table)

