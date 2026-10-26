#include <winsock2.h>
#include <ws2tcpip.h>

void net_init() {
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2,2), &wsaData);
}

int net_connect(const char* ip, int port) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) return -1;

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(port);
    server.sin_addr.s_addr = inet_addr(ip);

    int res = connect(s, (struct sockaddr *)&server, sizeof(server));
    if (res == SOCKET_ERROR) {
        closesocket(s);
        return -1;
    }
    return (int)s;
}

void net_close(int s) {
    closesocket(s);
}