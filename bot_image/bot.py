import os
from dotenv import load_dotenv
import logging
import re
import paramiko
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

import psycopg2
from psycopg2 import Error
#from test_findemail import findEmailsCommand, findEmails, confirmAddEmails, cancel, CONFIRM_ADD_EMAILS



TOKEN = "6897089865:AAFd-_o25dFnvpfwHPCEuFwTEKzm6DrlzYc"

# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
VERIFY_PASSWORD, GET_APT_LIST, CHOOSE_MODE, SEARCH_PACKAGE = range(4)
#для состояния добавления email адреса
# Новая константа для состояния подтверждения добавления номеров телефонов в базу данных
CONFIRM_ADD_PHONE_NUMBERS = 1

# Настройки SSH-соединения
SSH_HOST = os.getenv("SSH_HOST", "192.168.37.137")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USERNAME = os.getenv("SSH_USERNAME", "deb")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "1")

# Настройки подключения к базе данных
DB_USER = os.getenv("POSTGRESQL_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRESQL_PASSWORD", "eve")
DB_HOST = os.getenv("POSTGRESQL_HOST", "192.168.37.137")
DB_PORT = int(os.getenv("POSTGRESQL_PORT", 5432))
DB_NAME = os.getenv("POSTGRESQL_DB", "kuma8")










def ssh_command(command):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        ssh_client.close()
        return output
    except paramiko.AuthenticationException:
        return "Ошибка аутентификации. Проверьте правильность имени пользователя и пароля."
    except paramiko.SSHException as e:
        return f"Ошибка при установке SSH-соединения: {e}"
    except Exception as e:
        return f"Ошибка: {e}"

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет, {user.full_name}! Вот список доступных команд:\n'
                              '/find_email - Найти email адреса\n'
                              '/find_phone_number - Найти номера телефонов\n'
                              '/verify_password - Проверить сложность пароля\n'
                              '/get_services - Получить список сервисов\n'
                              '/get_release - Получить информацию о версии ОС\n'
                              '/get_uname - Получить информацию о ядре\n'
                              '/get_uptime - Получить информацию о времени работы системы\n'
                              '/get_df - Получить информацию о дисковом пространстве\n'
                              '/get_free - Получить информацию о памяти\n'
                              '/get_mpstat - Получить статистику процессора\n'
                              '/get_w - Получить информацию о пользователях\n'
                              '/get_auths - Получить информацию о последних авторизациях\n'
                              '/get_critical - Получить критические сообщения из журнала системы\n'
                              '/get_ps - Получить список запущенных процессов\n'
                              '/get_ss - Получить список слушающих сокетов\n'
                              '/get_apt_list - Получить информацию об установленных пакетах\n')

def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Введите пароль для проверки или отправьте /cancel чтобы отменить операцию.')
    return VERIFY_PASSWORD

def verifyPassword(update: Update, context):
    password = update.message.text
    # Проверяем пароль на соответствие требованиям
    if (len(password) >= 8 and
            any(char.isupper() for char in password) and
            any(char.islower() for char in password) and
            any(char.isdigit() for char in password) and
            any(char in '!@#$%^&*().' for char in password)):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')
    return ConversationHandler.END

def cancel(update: Update, context):
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END




def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска номеров телефонов или отправьте /cancel чтобы отменить операцию.')
    return 'findPhoneNumbers'

def insert_phone_to_db(phone):
    connection = None
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME)
        cursor = connection.cursor()

        # Выполнение SQL-запроса для вставки номера телефона
        cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s);", (phone,))
        connection.commit()

        # Логирование успешного выполнения операции
        logging.info("Номер телефона успешно добавлен в базу данных")
    except (Exception, Error) as error:
        # Логирование ошибки, если она произошла
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
        raise
    finally:
        # Закрытие соединения с базой данных
        if connection is not None:
            cursor.close()
            connection.close()
            logging.info("Соединение с PostgreSQL закрыто")

def findPhoneNumbers(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем текст, содержащий(или нет) номера телефонов
    phoneRegex = re.compile(
        r'(\+?[78]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})')  # Регулярное выражение для номеров телефонов
    phoneList = phoneRegex.findall(user_input)  # Ищем номера телефонов
    if not phoneList:  # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Ничего не найдено')
        return ConversationHandler.END
    else:
        # Устанавливаем phone_numbers в контексте
        context.user_data['phone_numbers'] = phoneList
        phones = ''  # Создаем строку, в которую будем записывать номера телефонов
        for i, phone in enumerate(phoneList, start=1):
            formatted_phone = re.sub(r'\D', '', phone)  # Убираем все нецифровые символы из номера
            if formatted_phone.startswith('7'):
                formatted_phone = '+7' + formatted_phone[1:]
            elif not (formatted_phone.startswith('7') or formatted_phone.startswith('8')):
                formatted_phone = '8' + formatted_phone
            phones += f'{i}. {formatted_phone}\n'  # Записываем очередной номер телефона
        update.message.reply_text(phones)  # Отправляем сообщение пользователю
        # После вывода номеров телефонов предлагаем сохранить их в базу данных
        update.message.reply_text('Хотите сохранить найденные номера телефонов в базу данных? (Да/Нет)')
        return CONFIRM_ADD_PHONE_NUMBERS


def confirmAddPhoneNumbers(update: Update, context: CallbackContext):
    choice = update.message.text.lower()
    if choice == 'да':
        phone_numbers = context.user_data.get('phone_numbers')
        if phone_numbers:
            for phone_number in phone_numbers:
                try:
                    insert_phone_to_db(phone_number)
                    update.message.reply_text(f'Номер телефона {phone_number} успешно добавлен в базу данных')
                except Exception as e:
                    update.message.reply_text(f'Ошибка при добавлении номера телефона {phone_number}: {e}')
    else:
        update.message.reply_text('Номера телефонов не будут добавлены в базу данных.')

    return ConversationHandler.END

CONFIRM_ADD_EMAILS = range(1) #для состояния добавления email адреса


def cancel(update: Update, context):
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

def findEmailsCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email-адресов или отправьте /cancel чтобы отменить операцию.')
    return 'findEmails'

def insert_email_to_db(email):
    connection = None
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME)
        cursor = connection.cursor()

        # Выполнение SQL-запроса для вставки email
        cursor.execute("INSERT INTO emails (email) VALUES (%s);", (email,))
        connection.commit()

        # Логирование успешного выполнения операции
        logging.info("Email успешно добавлен в базу данных")
    except (Exception, Error) as error:
        # Логирование ошибки, если она произошла
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
        raise
    finally:
        # Закрытие соединения с базой данных
        if connection is not None:
            cursor.close()
            connection.close()
            logging.info("Соединение с PostgreSQL закрыто")

def findEmails(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем текст, содержащий(или нет) email-адреса
    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')  # Регулярное выражение для email-адресов
    emailList = emailRegex.findall(user_input)  # Ищем email-адреса
    if not emailList:  # Обрабатываем случай, когда email-адресов нет
        update.message.reply_text('Ничего не найдено')
        return ConversationHandler.END
    else:
        context.user_data['emails'] = emailList  # Сохраняем email-адреса в контексте пользователя
        update.message.reply_text('Найдены следующие email-адреса:\n' + '\n'.join(emailList))
        update.message.reply_text('Хотите добавить эти email-адреса в базу данных? (Да/Нет)')
        return CONFIRM_ADD_EMAILS
    
def confirmAddEmails(update: Update, context: CallbackContext):
    choice = update.message.text.lower()
    if choice in ['да', 'нет']:
        if choice == 'да':
            emails = context.user_data.get('emails')
            if emails:
                for email in emails:
                    try:
                        insert_email_to_db(email)
                        update.message.reply_text(f'Email {email} успешно добавлен в базу данных')
                    except Exception as e:
                        update.message.reply_text(f'Ошибка при добавлении email {email}: {e}')
        else:
            update.message.reply_text('Данные не будут добавлены в базу данных.')
    else:
        update.message.reply_text('Пожалуйста, ответьте "Да" или "Нет".')
    return ConversationHandler.END


def get_services(update: Update, context):
    services_info = ssh_command("systemctl list-units --type=service --state=running")
    update.message.reply_text(services_info)

def get_release(update: Update, context: CallbackContext):
    release_info = ssh_command("lsb_release -a")
    update.message.reply_text(release_info)

def get_uname(update: Update, context: CallbackContext):
    uname_info = ssh_command("uname -a")
    update.message.reply_text(uname_info)

def get_uptime(update: Update, context: CallbackContext):
    uptime_info = ssh_command("uptime")
    update.message.reply_text(uptime_info)

def get_df(update: Update, context: CallbackContext):
    df_info = ssh_command("df -h")
    update.message.reply_text(df_info)

def get_free(update: Update, context: CallbackContext):
    free_info = ssh_command("free -h")
    update.message.reply_text(free_info)

def get_mpstat(update: Update, context: CallbackContext):
    mpstat_info = ssh_command("mpstat")
    update.message.reply_text(mpstat_info)

def get_w(update: Update, context: CallbackContext):
    w_info = ssh_command("w")
    update.message.reply_text(w_info)

def get_auths(update: Update, context: CallbackContext):
    auths_info = ssh_command("last -n 10")
    update.message.reply_text(auths_info)

def get_critical(update: Update, context: CallbackContext):
    critical_info = ssh_command("journalctl -p 0..3 -n 5")
    update.message.reply_text(critical_info)

def get_ps(update: Update, context: CallbackContext):
    ps_info = ssh_command("ps aux | head -n 45")
    update.message.reply_text(ps_info)

def get_ss(update: Update, context: CallbackContext):
    ss_info = ssh_command("ss -tuln")
    update.message.reply_text(ss_info)

def get_apt_list(update: Update, context: CallbackContext):
    update.message.reply_text("Выберите режим работы:\n1. Вывод всех пакетов\n2. Поиск информации о пакете")
    return CHOOSE_MODE

def choose_mode(update: Update, context: CallbackContext):
    choice = update.message.text
    if choice == '1':
        # Вывод всех пакетов
        all_packages_info = ssh_command("dpkg -l | tail -n +6 | head -n 10")
        update.message.reply_text(all_packages_info)
        return ConversationHandler.END
    elif choice == '2':
        # Запрашиваем у пользователя название пакета для поиска информации
        update.message.reply_text("Введите название пакета:")
        return SEARCH_PACKAGE
    else:
        update.message.reply_text("Некорректный выбор. Пожалуйста, выберите 1 или 2.")
        return CHOOSE_MODE

def search_package(update: Update, context: CallbackContext):
    package_name = update.message.text
    package_info = ssh_command(f"dpkg -l | grep -i {package_name}")
    update.message.reply_text(package_info)
    return ConversationHandler.END
def get_repl_logs(update: Update, context: CallbackContext):
    try:
        # Установка SSH-соединения
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=DB_HOST, port=DB_PORT, username=DB_USER, password=DB_PASSWORD)

        # Выполнение команды на удаленном сервере
        stdin, stdout, stderr = ssh_client.exec_command("cat /var/log/postgresql/postgresql-15-main.log | tail -n 8")
        logs = stdout.read().decode()

        # Закрытие SSH-соединения
        ssh_client.close()

        # Отправка логов пользователю
        update.message.reply_text(logs)
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {e}")

def execute_sql_and_send_result(update: Update, context: CallbackContext, sql_query: str):
    try:
        connection = psycopg2.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME)

        cursor = connection.cursor()
        cursor.execute(sql_query)
        data = cursor.fetchall()
        result_message = '\n'.join(map(str, data))  # Преобразование данных в строку для отправки

        # Отправка результата пользователю
        update.message.reply_text(result_message)
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        update.message.reply_text("Произошла ошибка при выполнении команды.")
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

def get_emails(update: Update, context: CallbackContext):
    sql_query = "SELECT * FROM emails;"
    execute_sql_and_send_result(update, context, sql_query)

def get_phone_numbers(update: Update, context: CallbackContext):
    sql_query = "SELECT * FROM phone_numbers;"
    execute_sql_and_send_result(update, context, sql_query)

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher


    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            CONFIRM_ADD_EMAILS: [MessageHandler(Filters.regex('^(Да|да)$'), confirmAddEmails),
                                MessageHandler(Filters.regex('^(Нет|нет)$'), cancel)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчик в диспетчер
    dp.add_handler(convHandlerFindEmails)

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))

    # Добавляем обработчик для проверки пароля
    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(convHandlerVerifyPassword)

    # Обработчик диалога для подтверждения добавления номеров телефонов в базу данных
    dp.add_handler(CommandHandler("find_phone_number", findPhoneNumbersCommand))

    # Создаем ConversationHandler для подтверждения добавления номеров в базу данных
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
        states={
            CONFIRM_ADD_PHONE_NUMBERS: [MessageHandler(Filters.regex('^(Да|да|Нет|нет)$'), confirmAddPhoneNumbers)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv_handler)


    

    # Обработчик диалога для поиска email-адресов и подтверждения добавления
    #dp.add_handler(convHandlerFindEmails)
    # Добавляем остальные обработчики команд
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    # Создаем обработчик команды /get_apt_list
    apt_list_handler = ConversationHandler(
        entry_points=[CommandHandler("get_apt_list", get_apt_list)],
        states={
            CHOOSE_MODE: [MessageHandler(Filters.text & ~Filters.command, choose_mode)],
            SEARCH_PACKAGE: [MessageHandler(Filters.text & ~Filters.command, search_package)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Добавляем обработчик команды в диспетчер
    dp.add_handler(apt_list_handler)

    # Запускаем бота
    updater.start_polling()

    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()