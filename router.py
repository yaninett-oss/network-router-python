"""
router.py — программный маршрутизатор.

Практическая работа №2. Создание программного маршрутизатора
и многоклиентской сети.

Маршрутизатор:
- принимает TCP-клиентов на 127.0.0.1:5000;
- принимает UDP-клиентов на 127.0.0.1:6000;
- регистрирует клиентов по имени (REGISTER|ClientN);
- маршрутизирует сообщения между подсетями;
- обрабатывает приоритеты (HIGH / NORMAL);
- ведёт статистику трафика;
- поддерживает команды /list и /stats.
"""

import socket
import json
import threading
import time
import queue
import datetime

# -----------------------------------------------------------------
# Настройки маршрутизатора
# -----------------------------------------------------------------

HOST = "127.0.0.1"
TCP_PORT = 5000
UDP_PORT = 6000

LOG_FILE = "router.log"

# -----------------------------------------------------------------
# ANSI-цвета для вывода в консоль
# -----------------------------------------------------------------

COLOR_RESET = "\033[0m"
COLOR_HIGH = "\033[91m"     # красный
COLOR_NORMAL = "\033[92m"   # зелёный
COLOR_SYSTEM = "\033[96m"   # голубой
COLOR_WARN = "\033[93m"     # жёлтый

# -----------------------------------------------------------------
# Загрузка таблицы клиентов
# -----------------------------------------------------------------

with open("clients.json", "r", encoding="utf-8") as file:
    clients = json.load(file)

# Подключённые в данный момент клиенты
# { "Client1": {"socket": ..., "address": ..., "protocol": "TCP"} }
connected_clients = {}

# Статистика
stats = {
    "tcp": 0,
    "udp": 0,
    "high": 0,
    "normal": 0,
    "same_subnet": 0,
    "cross_subnet": 0,
}

# Очередь приоритетных сообщений
# Меньшее число = выше приоритет
priority_queue = queue.PriorityQueue()

# Счётчик для очереди (чтобы сохранять порядок при равных приоритетах)
queue_counter = 0

# -----------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------

def log(text):
    """Записать строку в лог-файл и вывести в консоль."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {text}"

    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")

    print(line)


def color_priority(priority):
    """Вернуть цветной текст приоритета."""
    if priority == "HIGH":
        return f"{COLOR_HIGH}[HIGH]{COLOR_RESET}"
    return f"{COLOR_NORMAL}[NORMAL]{COLOR_RESET}"


# -----------------------------------------------------------------
# Отправка сообщения клиенту
# -----------------------------------------------------------------

def send_to_client(target, message):
    """Отправить сообщение клиенту по имени."""
    if target not in connected_clients:
        log(f"[ROUTER] Клиент {target} не подключён.")
        return

    client = connected_clients[target]

    try:
        if client["protocol"] == "TCP":
            client["socket"].send(message.encode("utf-8"))
        elif client["protocol"] == "UDP":
            client["socket"].sendto(
                message.encode("utf-8"),
                client["address"]
            )
    except Exception as error:
        log(f"[ROUTER] Ошибка отправки {target}: {error}")


# -----------------------------------------------------------------
# Обработка сообщения (маршрутизация)
# -----------------------------------------------------------------

def process_message(sender, message):
    """Разобрать сообщение и переслать его получателю."""
    global queue_counter

    # Команды
    if message.strip() == "/list":
        list_clients(sender)
        return

    if message.strip() == "/stats":
        show_stats(sender)
        return

    parts = message.split("|", 2)

    if len(parts) != 3:
        log(f"[ROUTER] Неверный формат сообщения от {sender}.")
        return

    target = parts[0].strip()
    priority = parts[1].strip().upper()
    text = parts[2]

    if target not in clients:
log(f"[ROUTER] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]

    # Автоматический приоритет: если пользователь HIGH — сообщение тоже HIGH
    if sender_info["priority"] == "HIGH":
        priority = "HIGH"

    if priority not in ("HIGH", "NORMAL"):
        priority = "NORMAL"

    # Обновляем статистику
    if sender_info["protocol"] == "TCP":
        stats["tcp"] += 1
    else:
        stats["udp"] += 1

    if priority == "HIGH":
        stats["high"] += 1
    else:
        stats["normal"] += 1

    if sender_info["subnet"] == target_info["subnet"]:
        stats["same_subnet"] += 1
        cross = False
    else:
        stats["cross_subnet"] += 1
        cross = True

    # Вывод информации
    log("")
    log(f"{COLOR_SYSTEM}[ROUTER] ПОЛУЧЕНО СООБЩЕНИЕ{COLOR_RESET}")
    log(f"  Отправитель:        {sender} ({sender_info['ip']})")
    log(f"  Получатель:         {target} ({target_info['ip']})")
    log(f"  Подсеть отправителя: {sender_info['subnet']}")
    log(f"  Подсеть получателя:  {target_info['subnet']}")
    log(f"  Протокол отправителя: {sender_info['protocol']}")
    log(f"  Протокол получателя:  {target_info['protocol']}")
    log(f"  Приоритет:           {color_priority(priority)}")
    log(f"  Сообщение:           {text}")

    if priority == "HIGH":
        log(f"{COLOR_HIGH}[ROUTER] Приоритетное сообщение.{COLOR_RESET}")

    if cross:
        log("[ROUTER] Выполняется межсетевой маршрут.")

    if sender_info["protocol"] != target_info["protocol"]:
        log("[ROUTER] Выполняется преобразование протокола.")

    result = f"[{priority}] {sender} → {target}: {text}"

    # Обработка очереди: HIGH — сразу, NORMAL — с задержкой
    if priority == "HIGH":
        send_to_client(target, result)
    else:
        # задержка для обычного трафика
        time.sleep(1)
        send_to_client(target, result)


# -----------------------------------------------------------------
# Команды /list и /stats
# -----------------------------------------------------------------

def list_clients(requester):
    """Показать список подключённых клиентов."""
    log("")
    log(f"{COLOR_SYSTEM}[ROUTER] /list — подключённые клиенты:{COLOR_RESET}")
    if not connected_clients:
        log("  (никто не подключён)")
    else:
        for name, info in connected_clients.items():
            log(f"  {name:<10} {info['protocol']:<4} {clients[name]['ip']:<15} {clients[name]['subnet']}")


def show_stats(requester):
    """Показать статистику трафика."""
    log("")
    log(f"{COLOR_SYSTEM}========== СТАТИСТИКА =========={COLOR_RESET}")
    log(f"  TCP сообщений:      {stats['tcp']}")
    log(f"  UDP сообщений:      {stats['udp']}")
    log(f"  HIGH:               {stats['high']}")
    log(f"  NORMAL:             {stats['normal']}")
    log(f"  Внутри одной подсети: {stats['same_subnet']}")
    log(f"  Межсетевых:         {stats['cross_subnet']}")
    log(f"{COLOR_SYSTEM}================================{COLOR_RESET}")


# -----------------------------------------------------------------
# Обработка TCP-клиента
# -----------------------------------------------------------------

def handle_tcp_client(client_socket, client_address):
    """Обслуживание одного TCP-клиента в отдельном потоке."""
    sender = None

    try:
        # Первое сообщение — регистрация
        registration = client_socket.recv(1024).decode("utf-8")

        if registration.startswith("REGISTER|"):
            sender = registration.split("|")[1].strip()

            if sender not in clients:
                client_socket.send("Ошибка: клиент не найден в clients.json".encode("utf-8"))
                client_socket.close()
                return

            connected_clients[sender] = {
                "socket": client_socket,
                "address": client_address,
                "protocol": "TCP"
            }

            log("")
log(f"{COLOR_SYSTEM}[ROUTER] TCP-клиент подключён: {sender}{COLOR_RESET}")
            log(f"  Адрес:     {client_address}")
            log(f"  Подсеть:   {clients[sender]['subnet']}")
            log(f"  Приоритет: {clients[sender]['priority']}")

            client_socket.send("Регистрация выполнена.".encode("utf-8"))

        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode("utf-8")
            process_message(sender, message)

    except Exception as error:
        log(f"[ROUTER] Ошибка TCP-клиента {sender}: {error}")

    finally:
        if sender in connected_clients:
            del connected_clients[sender]
        client_socket.close()
        log(f"[ROUTER] Клиент {sender} отключён.")


# -----------------------------------------------------------------
# TCP-сервер маршрутизатора
# -----------------------------------------------------------------

def tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind((HOST, TCP_PORT))
    tcp_socket.listen()

    log(f"{COLOR_SYSTEM}[ROUTER] TCP ожидает подключения: {HOST}:{TCP_PORT}{COLOR_RESET}")

    while True:
        client_socket, client_address = tcp_socket.accept()
        thread = threading.Thread(
            target=handle_tcp_client,
            args=(client_socket, client_address)
        )
        thread.start()


# -----------------------------------------------------------------
# UDP-сервер маршрутизатора
# -----------------------------------------------------------------

def udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, UDP_PORT))

    log(f"{COLOR_SYSTEM}[ROUTER] UDP ожидает сообщения: {HOST}:{UDP_PORT}{COLOR_RESET}")

    while True:
        data, client_address = udp_socket.recvfrom(1024)
        message = data.decode("utf-8")

        if message.startswith("REGISTER|"):
            sender = message.split("|")[1].strip()

            if sender not in clients:
                udp_socket.sendto(
                    "Ошибка: клиент не найден в clients.json".encode("utf-8"),
                    client_address
                )
                continue

            connected_clients[sender] = {
                "socket": udp_socket,
                "address": client_address,
                "protocol": "UDP"
            }

            log("")
            log(f"{COLOR_SYSTEM}[ROUTER] UDP-клиент подключён: {sender}{COLOR_RESET}")
            log(f"  Адрес:     {client_address}")
            log(f"  Подсеть:   {clients[sender]['subnet']}")
            log(f"  Приоритет: {clients[sender]['priority']}")

            udp_socket.sendto(
                "Регистрация выполнена.".encode("utf-8"),
                client_address
            )

        else:
            sender = None
            for name, client in connected_clients.items():
                if (client["protocol"] == "UDP"
                        and client["address"] == client_address):
                    sender = name
                    break

            if sender:
                process_message(sender, message)
            else:
                log(f"[ROUTER] Сообщение от неизвестного UDP-адреса: {client_address}")


# -----------------------------------------------------------------
# Запуск маршрутизатора
# -----------------------------------------------------------------

if __name__ == "__main__":
    print(f"{COLOR_SYSTEM}========================================{COLOR_RESET}")
    print(f"{COLOR_SYSTEM}   ПРОГРАММНЫЙ МАРШРУТИЗАТОР{COLOR_RESET}")
    print(f"{COLOR_SYSTEM}========================================{COLOR_RESET}")
    print(f"  TCP порт: {TCP_PORT}")
    print(f"  UDP порт: {UDP_PORT}")
    print(f"  Клиентов в таблице: {len(clients)}")
    print(f"  Лог-файл: {LOG_FILE}")
print(f"{COLOR_SYSTEM}========================================{COLOR_RESET}")

    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    udp_thread = threading.Thread(target=udp_server, daemon=True)

    tcp_thread.start()
    udp_thread.start()

    # Держим главный поток живым
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ROUTER] Завершение работы.")