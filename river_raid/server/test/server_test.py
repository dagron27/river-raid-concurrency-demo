from river_run.server.network.network import ServerNetwork

if __name__ == "__main__":
    server = ServerNetwork()
    server.start_service()
    try:
        server.accept_connection()
    except KeyboardInterrupt:
        print("Server interrupted")
    finally:
        server.close_service()
