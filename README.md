## 

1. Устанавливаем виртуальное окружение 
   ```
   python3 -m venv venv
   ```

2. Активируем виртуальное окружение
   
   Windows
   ```
   .\venv\Scripts\activate
   ```

   Linux 
   ```
   source venv/bin/activate
   ```

3. Запускаем скрипт
   ```
   python main.py
   ```

    > Заметка: при первом запуске создадутся все необходимые файлы. 
    > - accounts.txt
    > - proxys.txt
    > - bad_token.txt
    > - locked.txt
    > - suspended.txt
    > - log.txt
    > - tasks.json

    > После создания файлов обязательно остановите программу и выполните шаг 4.

4. Добавьте токены твиттер в accounts.txt и прокси в proxys.txt и запустите скрипт снова.

5. В папке data есть файл settings.py, там можно поставить задержку между действиями и повторное кол-во попыток в случае ошибки.
