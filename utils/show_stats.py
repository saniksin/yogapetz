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

    wallets = {
        "wallets": 0,
        "not_mint": 0
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
            wallets["wallets"] += 1
            if all(int(row[rarity]) == 0 for rarity in ["uncommon", "rare", "legendary", "mythical"]):
                wallets["not_mint"] += 1


    # Выводим таблицу
    print(table)

    # Вычисляем общее количество для расчета процентов
    total_nft = sum(total_stats.values())
    total_wallets = wallets["wallets"]
    not_mint = wallets["not_mint"]

    # Выводим общую статистику с процентами
    total_table = PrettyTable()
    total_table.field_names = ["Type", "Total", "Percentage"]
    for nft_type, total in total_stats.items():
        percentage = (total / total_nft) * 100 if total_nft > 0 else 0
        total_table.add_row([nft_type.capitalize(), total, f"{percentage:.2f}%"])

    print("Общая статистика: \n\n"
          f"Всего NFT: {total_nft}. \n"
          f"Всего кошельков: {total_wallets}.\n" 
          f"Кошельков не минтили: {not_mint}.\n"
          f"Кошельков сминтили: {total_wallets - not_mint}")
    print(total_table)
