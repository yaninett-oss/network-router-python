"""
client_tcp.py — TCP-клиент.

Запуск:
    python client_tcp.py Client1
    python client_tcp.py Client2
    python client_tcp.py Client3
    python client_tcp.py Client7

Клиент:
- подключается к маршрутизатору (127.0.0.1:5000) по TCP;
- регистрируется под именем, переданным в аргументе;
- отправляет сообщения в формате: получатель|приоритет|текст;
- принимает входящие сообщения от маршрутизатора.
"""

import socket
import sys
import threading


HOST = "127.0.0.1"
TCP_PORT = 5000


# -----------------------------------------------------------------
# Приём сообщений от маршрутизатора (в отдельном потоке)
# -----------------------------------------------------------------

def receive_messages(client_socket, name):
    """Постоянно получать входящие сообщения от маршрутизатора."""
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                print(f"\n[{name}] Соединение закрыто маршрутизатором.")
                break
            print(f"\n[{name}] ВХОДЯЩЕЕ: {data.decode('utf-8')}")
            print("> ", end="", flush=True)
        except Exception as error:
            print(f"\n[{name}] Ошибка приёма: {error}")
            break


# -----------------------------------------------------------------
# Основная логика клиента
# -----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Использование: python client_tcp.py <ИмяКлиента>")
        print("Пример:        python client_tcp.py Client1")
        sys.exit(1)

    name = sys.argv[1].strip()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, TCP_PORT))

    # Регистрация
    client_socket.send(f"REGISTER|{name}".encode("utf-8"))
    response = client_socket.recv(1024).decode("utf-8")
    print(f"[{name}] {response}")

    # Поток приёма входящих
    receiver = threading.Thread(
        target=receive_messages,
        args=(client_socket, name),
        daemon=True
    )
    receiver.start()

    print(f"[{name}] Формат: получатель|приоритет|сообщение")
    print(f"[{name}] Пример: Client4|HIGH|Привет!")
    print(f"[{name}] Команды: /list, /stats, exit")
    print()

    while True:
        try:
            message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not message:
            continue

        if message.lower() == "exit":
            break

        # Отправка на маршрутизатор
        try:
            client_socket.send(message.encode("utf-8"))
        except Exception as error:
            print(f"[{name}] Ошибка отправки: {error}")
            break

    client_socket.close()
    print(f"[{name}] Клиент завершил работу.")


if __name__ == "__main__":
    main()