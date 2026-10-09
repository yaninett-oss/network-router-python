"""
client_udp.py — UDP-клиент.

Запуск:
    python client_udp.py Client4
    python client_udp.py Client5
    python client_udp.py Client6

Клиент:
- подключается к маршрутизатору (127.0.0.1:6000) по UDP;
- регистрируется под именем, переданным в аргументе;
- отправляет сообщения в формате: получатель|приоритет|текст;
- принимает входящие сообщения от маршрутизатора.
"""

import socket
import sys
import threading


HOST = "127.0.0.1"
UDP_PORT = 6000


# -----------------------------------------------------------------
# Приём сообщений от маршрутизатора (в отдельном потоке)
# -----------------------------------------------------------------

def receive_messages(client_socket, name):
    """Постоянно получать входящие UDP-датаграммы."""
    while True:
        try:
            data, _ = client_socket.recvfrom(1024)
            if not data:
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
        print("Использование: python client_udp.py <ИмяКлиента>")
        print("Пример:        python client_udp.py Client4")
        sys.exit(1)

    name = sys.argv[1].strip()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Регистрация
    client_socket.sendto(f"REGISTER|{name}".encode("utf-8"), (HOST, UDP_PORT))
    data, _ = client_socket.recvfrom(1024)
    print(f"[{name}] {data.decode('utf-8')}")

    # Поток приёма входящих
    receiver = threading.Thread(
        target=receive_messages,
        args=(client_socket, name),
        daemon=True
    )
    receiver.start()

    print(f"[{name}] Формат: получатель|приоритет|сообщение")
    print(f"[{name}] Пример: Client1|HIGH|Привет!")
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
            client_socket.sendto(message.encode("utf-8"), (HOST, UDP_PORT))
        except Exception as error:
            print(f"[{name}] Ошибка отправки: {error}")
            break

    client_socket.close()
    print(f"[{name}] Клиент завершил работу.")


if __name__ == "__main__":
    main()