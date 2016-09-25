from WebProxy import WebProxy

def main():
    proxy = WebProxy(port = 8080)

    proxy.start()


if __name__ == "__main__":
    main()
